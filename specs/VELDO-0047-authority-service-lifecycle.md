---
schema: veldo.spec/v1
id: VELDO-0047
title: Authority service installation, startup, stop, and absent-service behavior
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W32
plan_revision: 3
depends_on: [VELDO-0023, VELDO-0025, VELDO-0027, VELDO-0029, VELDO-0040, VELDO-0046, VELDO-0107]
placement: [fleet, loop, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/supervisor.py"
  - ".veldo/supervisor.py"
  - "packs/*/.veldo/supervisor.py"
  - "engine/.veldo/status_server.py"
  - ".veldo/status_server.py"
  - "packs/*/.veldo/status_server.py"
  - "engine/.veldo/control_service*.py"
  - ".veldo/control_service*.py"
  - "packs/*/.veldo/control_service*.py"
  - "engine/.veldo/control_client*.py"
  - ".veldo/control_client*.py"
  - "packs/*/.veldo/control_client*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/services/veldo-authority*.service"
  - ".veldo/services/veldo-authority*.service"
  - "packs/*/.veldo/services/veldo-authority*.service"
  - "scripts/suites/*_veldo_0047_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0047-authority-service-lifecycle.md"
  - "specs/index.md"
  - "proof/VELDO-0047/*"
behavior_bearing: true
observability:
  logs: >
    Record the operation, domain, repository, unit or request identity, accepted input versions,
    outcome and named refusal without secrets.
  metrics: >
    Count accepted and refused operations and expose current pending work for this specification.
  traces: >
    Join accepted inputs, actual service observations and resulting authority records by identity.
  error_taxonomy: >
    Distinguish invalid input, missing authority, stale subject, unavailable service,
    missing evidence and unknown outcome where applicable; never label unknown as success.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Explicit authorized installation/start/stop operates one protected Linux authority
      instance. Set and completeness: Install a disposable real systemd instance on this box and
      inspect fixed executable, configuration, enrollment, socket and helper permissions. Attempt a
      second scheduling instance under the same stable lock; it must refuse. Falsifier: Allow two
      instances to acquire scheduling authority; the single-instance observation must fail.
    falsified_by: >
      Allow two instances to acquire scheduling authority; the single-instance observation must
      fail.
  - id: AC2
    text: >
      Claim: Authenticated local client commands execute against the configured real authority store
      and return its committed result. Set and completeness: Send a signed mutation through
      production IPC with explicit domain, repository and workspace coordinates; query the
      configured SQLite database independently and compare changed row, journal identity and
      returned watermark. Wrong coordinates or actor must refuse. Falsifier: Return a callback
      success without changing the configured store; the independent SQLite observation must fail.
    falsified_by: >
      Return a callback success without changing the configured store; the independent SQLite
      observation must fail.
  - id: AC3
    text: >
      Claim: Absent authority and unexpected exit leave mutation/admission unavailable until an
      explicit operations action. Set and completeness: Stop the real service and invoke enabled
      local inspection, claim and mutation clients; require AUTHORITY_UNAVAILABLE, service identity,
      last-known watermark and start guidance, no local fallback, and clearly stale read-only state.
      Falsifier: Auto-start a service on a missing socket; the absent-service observation must fail.
    falsified_by: >
      Auto-start a service on a missing socket; the absent-service observation must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Authority service installation, startup, stop, and absent-service behavior. Deliver the normal function needed by the running factory journey.

## Context

W32 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## What the reviewer judges

- Normal use: an explicit, authorized install, start and stop runs one authority instance on this
  Linux host under systemd, with a fixed executable, configuration, enrollment, socket and helper
  permissions; a second instance under the same lock refuses. Authenticated local clients send signed
  commands over the production IPC with explicit domain, repository and workspace coordinates, and the
  service applies each to the configured SQLite store and returns the committed result and watermark.
  When the service is absent or has exited, mutation and admission stay unavailable
  (AUTHORITY_UNAVAILABLE, with the service identity, the last known watermark and start guidance), read
  state is marked stale, and nothing starts the service by itself or falls back to a local write.
  Installation also writes the launch receiver's configuration with this host's worker profile (see
  Notes).
- Threat model: two instances acquiring scheduling authority; a client command with the wrong
  coordinates or the wrong actor; a success reported by a callback that did not change the store; and an
  automatic start or a local fallback when the service is absent. The owner's account, systemd and the
  store file are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); automatic
  recovery (Release 2, see History); several profiles, remote inspection and the legacy status listener
  (Release 4); forged rows in our own store, files planted in the installed directory and resource
  exhaustion by our own account.

## Notes

This spec includes the normal request-to-real-store wiring identified by 0115 and the single
local service exclusion from 0030. Actual SQLite changes and returned committed watermarks are
required; callback-only evidence is insufficient. Optional legacy status-server/remote
inspection matrices are deferred; the new authenticated UI API is separately specified.

Handed on by VELDO-0040 (its review, 2026-09-24): the launch receiver refuses every local
launch whose configuration names no worker profile (invalid_input:profile:absent), and no
installer writes a receiver configuration today. Installing the authority on this host writes
the receiver configuration with this host's qualified linux-systemd profile (slice, lock and
caps).

Handed on by VELDO-0067 (its review, 2026-09-24): installation places the protected key
directory outside the home and temporary directories, because the custody wrapper denies a confined
worker every file created directly in an ancestor of that directory after the worker starts.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 1: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC2 automatic
recovery moved to Release 2; AC1 plural-profile and AC3/AC4 remote inspection/optional legacy
status listener breadth moved to Release 4. Local exclusion and actual IPC-to-SQLite
application are retained now. The criteria, declared evidence universe, Context and Notes
above now carry only the retained function. No specification status or historical proof was
changed.

2026-09-24, implementation (branch build-veldo-0047): `.veldo/control_service.py` installs one
authority instance for the enrolled workspaces of one domain on this Linux host (a fixed read-only
executable, a protected configuration, the enrollment signers this host trusted, one launch receiver
configuration per repository with this host's qualified linux-systemd worker profile, and a systemd
user unit rendered from `.veldo/services/veldo-authority.service` with no install section and no
restart), starts and stops it only on an explicit operations action, holds one scheduling instance
under a flock on the stable lock file beside the store, and applies signed commands arriving through
VELDO-0107's IPC to the configured store, returning the committed receipt and watermark.
`.veldo/control_client.py` names the service unit and the operations start procedure in every
AUTHORITY_UNAVAILABLE refusal and stale inspection. Installation refuses a key directory that is
absent or unsafe by name, with the exact one-time root step; suite 66 passes the location and the
worker directories explicitly, because this account can create nothing outside the home and temporary
directories without root. Suite 66_veldo_0047_authority (20 rows), red at b738c79, 24 mutations as
finding 47; scripts/check_teeth_mutations.py, outside the footprint, is touched only to register them.
Proof in proof/VELDO-0047/.

2026-09-24, landing: the footprint names scripts/check_teeth_mutations.py, where finding 47's
mutations are registered (the gate's shape check refuses a path no footprint names).

2026-09-24, review fixes (branch build-veldo-0047): the launch receiver installed into `<home>/bin`
refused every launch as unavailable_service:architecture_validator, because the installed modules were
a hand list without the validator its recheck loads from its own directory. `control_service.closure()`
now derives the fixed executable at installation from the entry points and the validator files
control_eligibility.VALIDATOR_ROLES declares, following every sibling load to a fixed point and refusing
by name a load of an absent module or one no literal names; `supervisor.py`, which the installer loads,
is laid down by the scaffolder. The key directory is refused as relative before anything resolves it,
judged by location before existence, and its one-time step creates only the directories missing below
the first existing ancestor and changes no existing directory. Suite 66 has 30 rows:
authority/installed-receiver-launches (a real launch through the installed receiver),
authority/installation-refuses-an-underivable-closure,
authority/key-directory-location-before-existence, authority/key-directory-guidance-changes-no-directory
and authority/key-directory-relative-refused are new, and installed-fixed-and-protected,
installed-assets and key-directory-placement judge the derived closure, an adopter's laid tree and the
new guidance; all eight are red by assertion at 7ed08fb. Finding 47 has 38 mutations.
