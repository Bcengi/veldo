# VELDO-0125 build and pending native checks

Candidate implementation, not a gate stamp, qualification, activation or independent
review. Specification status and acceptance criteria are unchanged. No real provider
login, engine invocation, live capture or deployed service was touched. The only
engine used by the native driver is 0124's synthetic engine.

## Implementation

Four canonical assets in `engine/.veldo` have identical installed `.veldo` copies:

* `control_routing.py`: selects a qualified, available host satisfying every
  accepted capability and the exact engine configuration digest. The reserved
  capabilities `macos` and `ios-build` require Darwin. Selection is deterministic
  in operator configuration order. The selected host, principal, profile digest,
  local runtime profile digest and complete requirement set enter the immutable
  0039 dispatch contract before launch. A blocked decision is journaled as a
  `host_routing` entity with its unit, dispatch, requirements and named reason.
* `control_worker_client.py`: signed claim, launch and result requests with explicit
  domain, repository, store and enrolled Linux workspace coordinates. The Mac clone
  path is distinct from that authority coordinate. Fixed SSH argv invokes the
  existing 0108 relay. A failed request returns AUTHORITY_UNAVAILABLE with service,
  last watermark and explicit start guidance. It opens no authority store.
* `control_worker_service.py`: an explicit Service subclass composed with 0047's
  existing serve function. It uses the same stable lock, SQLite connection, socket,
  enrollment, signature checks, local commands and observation log. It is the sole
  authority entry point for this configuration, never an additional server.
  The three families are `worker_claim`, `worker_launch` (accept and running), and
  `worker_result`. Inner command signatures, active scoped service membership with
  role `worker_receiver`, and the dispatch's assigned host principal are mandatory.
  Inner signatures use veldo-worker-command; outer relay requests use veldo-command.
  Acceptance, its ordinary 0036 pre-call reservation and the worker observation
  commit in one transaction before OS launch. Exit, spend report and observations
  also commit together. A refusal rolls back every command in that transaction.
  The wall allowance covers the remaining immutable dispatch deadline, including
  transport and startup delay; the host still enforces its smaller runtime cap.
  Each reservation facade has its own command registry, avoiding cross-instance
  handler collisions. The original invocation is derived from the stored claim.
* `control_worker.py`: the trusted Mac orchestration seam. It validates the host,
  runtime profile and account, uses 0124's preflight, run environment, supervisor,
  containment and ordinary descendant observations, and submits results under the
  retained binding. The engine never receives the client signing key. Configure its path in the
  qualified Mac profile's signing_keys list as well as protected paths; Seatbelt
  explicitly denies reading these files.

Result and separate `worker_spend` entities both retain domain, repository, store,
workspace, original unit, host, dispatch, contract and invocation identities.
They retain output/proof references, reported usage and the reservation receipt.
The result also retains process, terminal observation and each original signed
command's digest. Missing usage remains unknown charge; unknown OS outcomes retain
both slots. Terminal output never becomes landed completion. Retirement still
requires the existing cleanup, accounting and whole-group obligations.

The routing and command assets implement the spec's fleet placement; the Mac
bridge consumes the declared project_runner boundary; command and identity
validation implement its contracts placement. These are existing area ids. No
architecture contract or process exception is amended. All assets are in the
0125 footprint. Packs inherit them through ordinary engine composition;
`AC1/template-sync` assembles all seven and compares actual installed bytes.
The review amendment also changes the production launch, permission, ownership,
transaction and signing-key containment boundaries. Affected suites are run
individually; the canonical gate and native observations remain reviewer work.

## Integration contract

The trusted authority's admitted-unit path calls
`control_routing.prepare(dispatches, contract, profiles, now=...)` before handing
a dispatch to a host. Requirements are the accepted decision's
`input.context.required_host_capabilities`, copied by the Runner from the accepted
execution unit, never fields on a worker claim. The gate decision remains intact
so its ordinary stale-input check can revalidate it at receiver acceptance.
The result is either a persisted blocked decision or a prepared contract.
The production Runner calls this path whenever worker profiles or accepted unit
requirements exist. Requirements are copied from the accepted execution unit.
A remote route leaves the contract prepared for its receiver and never invokes
the local Linux receiver. Missing profiles with required capabilities block.

The explicit authority config adds `worker_profiles`. Each entry has `host`,
`principal`, `platform` (`linux` or `darwin`), positive `revision`, `capabilities`,
`engines` mapping adapter names to accepted configuration digests, `runtime_profile`
(the digest of the actual host supervisor profile), and Boolean `available`.
`qualification` has `kind: native`, an operator reviewed evidence `reference`,
and `profile_digest` computed over the entry excluding `qualification` and
`available`. Neither an eligible flag nor SSH access qualifies a host. Changing
capabilities or the runtime profile invalidates that evidence. Availability is
checked again at claim and acceptance; losing it cannot select Linux for Mac work.
A stopped service is unavailable; explicit operations must start it.

For an explicitly configured installation, the sole entry point is
`python3 .veldo/control_worker_service.py /absolute/protected/config.json`.
The existing installer is unchanged and does not activate this entry point.
The owner must integrate it into the fixed executable closure before deployment;
this build does not edit a deployed unit or enable real factory work.
The Mac's trusted supervisor calls `control_worker.run` with the remote client,
accepted clone, scratch and account profile. Its collector supplies real adapter
usage observations in production. The probe's explicit zero usage is synthetic
and cannot certify provider accounting.

## Development observations and single-change falsifiers

Only these two suites run, individually:

```
python3 scripts/selftest.py --suite 105_veldo_0125_relay
python3 scripts/selftest.py --suite 106_veldo_0125_routing
python3 proof/VELDO-0125/negative_controls.py
```

Both suites pass their six named 0125 rows. The dispatcher also runs 26 shared
checks and returns 2 for a selected PARTIAL run even with zero failures. These are
development observations, not accepted proof. No full selftest, canonical gate or
global mutation checker ran. The reviewer must verify the merged checkout.

Resume verification on 2026-10-10, implementation commit `83238f71`: each suite
was rerun once, sequentially, with six 0125 rows and 32 total checks passing,
zero failures, and the expected PARTIAL exit 2. Compilation passed for all 16
0125 Python assets and both suite registry files parsed. The three falsifiers
were regenerated against this commit because two retained source hashes
predated the final implementation edits. Native checks remain pending.

* AC1: `AC1/command-families` compares signed claims, both launch phases and result
  to independently read SQLite records and returned watermarks. `AC1/one-authority`
  submits each family to a failed relay and checks for a local store. The single
  change in `AC1.diff` creates a local SQLite store on failure; that named row fails.
  `AC1/authentication` refuses wrong coordinates and unsigned inner and outer
  commands. `AC1/template-sync` checks pack bytes; `AC1/native-declared` checks
  native driver syntax and its honest refusal on Linux.
* AC2: `AC2/capability-selection` covers neutral, macOS and combined macOS/iOS
  requirements. `AC2/host-routing-refusal` observes durable blocked decisions with
  the Mac unavailable. The single change in `AC2.diff` drops capability subset
  checking, permitting Linux fallback; that named row fails. `AC2/qualification`
  covers absent evidence, revision/configuration/capability changes, unavailable
  hosts at acceptance and a Linux profile asserting Mac capabilities.
  `AC2/actual-worker-launch` drives the production Mac orchestration and supervisor
  against explicit Apple fixtures, observes the chosen host and the authority's
  acceptance and reservation before bootstrap. `AC2/precall-caps` proves malformed
  runtime and exhausted spend allowance cannot lead to running state.
* AC3: `AC3/remote-result-binding` targets another existing dispatch, wrong unit,
  host, contract digest, process and actor; it observes no result or spend write.
  The single change in `AC3.diff` removes binding comparison; that named row fails.
  `AC3/unknown-charge` retains stopped work and unknown spend. The command-family
  row also reads both records through the ordinary owner-visible inspect command
  and compares output/proof references and usage to both result and spend
  records and the original reservation invocation.

`negative-controls.json` records each source hash, retained diff, suite log and
failed row. All three mutants were rejected. The logs include the dispatcher's
ordinary shared negative checks; only the named 0125 failures judge these mutants.

The production IPC attempt could not create AF_UNIX sockets: this sandbox returns
`PermissionError: [Errno 1] Operation not permitted` at socket creation, before
bind. The Linux suites therefore label their transport as an in-process fixture.
They still run the production Authority judge, enrollment resolver, both OpenSSH
signature checks, real Git, signed journal and real SQLite. They do not claim a
real socket, real SSH or Mac observation. This separate check preserves the real
IPC requirement and reports `not_run`, exit 2, in this sandbox:

```
python3 proof/VELDO-0125/ipc_checks.py > "$TMPDIR/veldo-0125-ipc.json" 2>&1
```

## Runnable native rows

Not run here. The selected Mac is `dmitrys-mac-mini`, observed by 0124 as
`dmitrys-mini.lan`, macOS 26.5.1 arm64. Prerequisites on the owner's logins are
working BatchMode SSH in both directions, this Linux account's alias as reachable
from the Mac, the existing Python/OpenSSH tools, and the Mac's pinned
`/opt/homebrew/bin/python3.12`. This does not use Claude Code or Codex logins.

From this committed Linux checkout, set `VELDO_LINUX_SSH_ALIAS` to that existing
SSH alias. Provision a dedicated Mac transport key, separate from the keyring
worker signing key. Put exactly this line in the Linux account's authorized_keys,
substituting the five bracketed values with the installation's absolute paths,
Mac tailnet address and transport public key:

```
restrict,from="<mac tailnet ip>",command="<python> <install>/.veldo/control_relay.py <fixed authority socket>" ssh-ed25519 <mac transport public key> veldo-mac-transport
```

The forced command owns the socket coordinate. The Mac supplies no remote command:

```
ssh -T -o BatchMode=yes -o IdentitiesOnly=yes -i "$MAC_TRANSPORT_KEY" "$VELDO_LINUX_SSH_ALIAS"
```

Set VELDO_AUTHORITY_SOCKET to the same fixed absolute socket path in that line,
and MAC_TRANSPORT_KEY to the absolute dedicated key path on the Mac. This exact command drives both engines and every row below:

```
python3 proof/VELDO-0125/native_roundtrip.py "$VELDO_LINUX_SSH_ALIAS" "$VELDO_AUTHORITY_SOCKET" "$MAC_TRANSPORT_KEY" > "$TMPDIR/veldo-0125-native.json" 2>&1
```

The driver exports tracked code to a new `~/veldo-0125-check-<unique>` directory
on the Mac, creates synthetic clones and a Mac-only receiver signing key, and
passes only its public key to a disposable Linux authority. It runs 0047's real
service and 0108's relay over real SSH, one authority at a time, and stops its child
in a finally block. It never changes a Git branch or existing worktree, production
service, real account profile or login. Private fixture keys stay in the printed
private temporary directory; do not commit them. The code export and public
results are retained for review.

For each `claude_code` and `codex` synthetic engine:

* `native/AC1/signed-families/<engine>`: compare the exact signed commands generated
  on the Mac with command digests and journal identities committed by Linux,
  including all coordinates and the returned watermark. Exercise each family
  after stopping the authority, through the same forced command and socket and verify no Mac-local SQLite file appears.
* `native/AC3/real-work/<engine>`: launch 0124's synthetic natural-exit engine under
  real launchd, Seatbelt, coalitions and kqueue through the remote worker path.
  Compare terminal/process observations, output/proof references and synthetic
  usage to independently read Linux result, spend and invocation records. A
  Mac-signed result naming another real running dispatch must refuse before the
  original result commits, despite authenticated SSH.

The Mac driver deliberately uses 0124's native candidate admission, skipping only
qualification, to measure the profile. Its candidate routing entry is explicitly
synthetic. No probe emits a qualification stamp or authorizes a real engine.
The authority allows ten minutes for setup and transfer; actual execution retains
its five second bound and ordinary stop escalation. Results include owner-readable
machine, unit, dispatch, state and spend, and the private path holding exact requests.

Lower-level exact commands, used by the driver, are available for diagnosis:

```
/opt/homebrew/bin/python3.12 proof/VELDO-0125/native_checks.py prepare codex
python3 proof/VELDO-0125/native_authority.py setup candidate.json "$TMPDIR/v125-new" "$VELDO_LINUX_SSH_ALIAS" "$VELDO_AUTHORITY_SOCKET" "$MAC_TRANSPORT_KEY"
python3 proof/VELDO-0125/native_authority.py serve "$TMPDIR/v125-new"
/opt/homebrew/bin/python3.12 proof/VELDO-0125/native_checks.py run codex client-codex.json
python3 proof/VELDO-0125/native_authority.py compare "$TMPDIR/v125-new" codex-result.json
```

Preparation and run execute on the Mac export; setup, serve and compare execute
on Linux. Transfer only candidate/client/result JSON as the driver does. Repeat
with `claude_code` and a fresh disposable authority. The one-command driver is
preferred because it supervises and stops the Linux child automatically.

Native transport, lifecycle observations and the canonical gate remain pending.
Reconnect, automatic recovery, broader host qualification and deployment activation remain
outside this specification's Release 1 build.

## Independent review fixes

The owner's assistant amended the production launch footprint in spec History.
These rows exercise the review findings on Linux with explicit host fixtures:

1. AC1/worker-mutate-only, worker-claim-only, worker-inbox-only and
   worker-request-only restrict the worker principal at the inner and outer
   boundaries. AC1/entity-owners rejects generic writes to dispatches, membership,
   verification keys and reservations. Each boundary has a retained falsifier.
2. AC2/production-routing uses Runner.submit and the real reservation and dispatch
   stores. AC2/production-account-host selects a Mac-only account profile. Required
   capabilities come from the accepted unit, without altering the gate's input
   identities. Removing the production prepare call fails the routing row.
3. AC2/precall-caps requires the exact prepared state after reservation refusal.
   AC3/refused-report-atomic requires unchanged entities, journal, commands and
   nonces after both the refused report and its retry. Removing the transaction
   fails each row separately.
4. 0124 AC1/worker-signing-key-read requires the explicit read denial. The native
   containment probe attempts an actual read of worker_signing_key. Its native
   and structural falsifiers remove that single read rule. The Mac worker also
   requires its client's signing key in the accepted profile's signing_keys list.
5. The native driver always uses the forced relay's fixed socket. It stops the
   authority before testing unavailability, with unchanged SSH argv. Transport
   credentials are separate from command signing credentials.
6. AC3/dispatch-other and native/AC3/dispatch-other create another running dispatch
   and send the wrong binding before committing the original result. The AC3
   binding falsifier must fail this specific case.
7. AC2/qualification checks a durable routing entity when the selected Mac becomes
   unavailable after preparation; AC2/host-routing-refusal covers initial absence.
8. AC1/signature-namespaces rejects outer-purpose signatures on inner commands and
   inner-purpose signatures on outer requests. The namespaces are veldo-command
   and veldo-worker-command respectively.

Review verification results are retained in review-verification.json. These are
selected suite results, never a canonical gate stamp. Native containment, real
Mac/SSH observations, qualification and activation remain unrun in this checkout.

The final selected pass observed 51 named 0124/0125 rows passing and rejected all
17 retained falsifiers. Across 88 affected suites, 51 passed and 37 remained
non-green. Confirmed limitations include denied Unix socket creation, an
unavailable qualified user manager, and denied fixture directories under
/run/user/1000. The verification record keeps all failing rows, including those
requiring unrestricted reviewer diagnosis; none is reported as a passing guard.
The service's fixed source closure resolves to 128 modules.

## Host verification of the affected suites

The 88 affected suites were rerun on the Linux host, outside the sandbox, from
2738378b. 18 were red there; each passed on a throwaway clone of main 294e1933, so
all 18 were caused by the change. Three fixes followed:

1. ea69f8be: control_launch.py loads control_routing.py on every dispatch, but the
   scaffold did not lay it down, so installed receivers refused every launch.
2. 66ccfe64 and f618f10d: membership, dispatch and reservation ownership was
   declared wherever those records were built (admit, the base authority Service,
   Dispatches, Reservations), bound to that copy's file. Setup, receivers and
   fixtures writing from another copy on the same store were then refused
   ownership_conflict, foreign_transition or entity_owned. The declarations now
   run only in the worker relay authority, through protect() beside each owning
   transition, which is where AC1/entity-owners observes them.

host_falsifiers.py reverts each fix in a clone of HEAD and requires the named row to
fail; host-falsifiers.json records 5 of 5 rejected. The 17 retained falsifiers were
rerun and all were rejected. After the fixes, 87 of the 88 suites pass.
86_veldo_0127_agent_configuration live/claude and live/codex stay pending. Their
live captures bind control_launch.py's digest, which this change alters, so they
need a fresh live capture against real logins. host-verification.json holds every
row.

## Ownership identified by code digest

An ownership declaration named one file path, so the same owner code from another
legitimate copy (the checkout's engine/.veldo, an installed .veldo, a fixture's copy)
was refused. On a relay installation the worker relay authority declares membership
from the installed engine, and a setup rerun from a checkout was then refused
ownership_conflict and foreign_transition. control_store.py now identifies the owning
code by the sha256 of its module bytes, checked the same way for every copy: a
registered transition must run from exactly one file whose bytes have the declared
digest, and a second declaration with the same owner, kinds and digest from another
path is the same declaration. The stored path is informational. A copy whose bytes
differ is refused at declaration (ownership_conflict) and at execution
(foreign_transition).

`AC1/owner-copies` in 105_veldo_0125_relay builds the relay authority from the
installed `.veldo`, then reruns membership protection and a change_roles command
through the checkout's `engine/.veldo` store and membership modules on the same store
(accepted, declarations unchanged), then through a copy with one appended comment
line (both refused, tables unchanged). Two single-change falsifiers, each applied to
both store copies in a throwaway tree, fail exactly that row:
`owner-copies-path-identity.diff` restores path identity and reproduces the defect
(same digest, refused by path); `owner-copies-digest-ignored.diff` drops the digest
comparison and accepts the edited copy. Logs are beside each diff.

Run on the host while another full gate was active, so only suites that use no user
systemd units or /run/user ran, through `run_suite.py` (no shared dispatcher checks):
105_veldo_0125_relay 15 of 15, 106_veldo_0125_routing 8 of 8, 59_veldo_0037_aliases
53 of 53 including aliases/owned-by-code-not-name. 86_veldo_0189_engine_upgrade, the
other ownership consumer, starts user units and was not run; it remains reviewer work.
