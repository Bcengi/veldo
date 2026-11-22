---
schema: veldo.spec/v1
id: VELDO-0359
title: Agent runs get no access to the Veldo store directory, enforced by one Landlock ruleset that is on by default and turned off by a visible marker, and their store reads are answered by their launch receiver
status: draft
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0052, VELDO-0127, VELDO-0208, VELDO-0254]
placement: [enforcement]
protected_paths: ["scripts/gate_unconfined.json"]
footprint:
  - .veldo/control_launch.py
  - engine/.veldo/control_launch.py
  - .veldo/control_clone.py
  - engine/.veldo/control_clone.py
  - .veldo/control_run_query.py
  - engine/.veldo/control_run_query.py
  - .veldo/control_eligibility.py
  - engine/.veldo/control_eligibility.py
  - .veldo/frontier.py
  - engine/.veldo/frontier.py
  - .veldo/runstatus.py
  - engine/.veldo/runstatus.py
  - .veldo/control_agent_config_handoff.py
  - engine/.veldo/control_agent_config_handoff.py
  - .veldo/init_scaffold.py
  - engine/.veldo/init_scaffold.py
  - scripts/suites/*_veldo_0359_*.py
  - scripts/suites/*.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - scripts/check_teeth_mutations.py
  - scripts/gate_unconfined.json
  - specs/VELDO-0359-agent-runs-cannot-reach-the-store.md
  - specs/index.md
  - proof/VELDO-0359/*
behavior_bearing: true
observability:
  logs: >
    Each local launch logs the sampled switch state (on, off with the marker path, or invalid), its
    preflight result (kernel probe reason, risky floor, store directory, store entries, mounts, runs
    location, placement, and for risky launches the effective-grant census), store_guard pending at
    acceptance and, separately, applied only when the wrapper's success byte arrives or enforce_failed
    with the step (audit, probe, create, add, restrict, unreported); a refusal names its reason, path and
    fix. The run query server logs each request name and outcome per dispatch, never arguments or answers.
  metrics: >
    Launches by store guard outcome (pending, applied, off, refused_switch, refused_kernel,
    refused_risky_floor, refused_layout, refused_census, enforce_failed by step, runner_started); run
    queries by request and outcome.
  traces: >
    The launch record carries store_guard (switch sample with marker path, preflight result, pending at
    acceptance, then applied, runner_started or enforce_failed with its step) and, at termination, the run
    query server's counts. The status command shows one store guard line for the enrolled store, which
    describes the configuration for later launches.
  error_taxonomy: >
    invalid_input:layout:switch (a present store-guard.off that is not a regular file of the account, or a
    failed check of it other than absence); unavailable_service:confinement:store_guard:<reason>
    (unsupported_platform, landlock_disabled, syscall_missing, syscall_blocked, abi_below_3; refused
    before acceptance); confined_runner_unavailable:platform and
    confined_runner_unavailable:landlock_abi_below_6 (risky floor, before acceptance);
    unavailable_service:confinement:store_guard:enforce:<step> (audit, probe, create, add, restrict or
    unreported, in the wrapper after acceptance and before any model code; no heartbeat child, no
    engine); invalid_input:layout:<element> (directory, entry, mount, runs, placement);
    confined_runner_unavailable:store_reachable (an effective risky grant reaches the store directory, or
    a required item cannot be resolved); confined_runner_unavailable:store_source (a seed or credential
    source resolves into it); unavailable_service:run_query (endpoint could not be made or made ready,
    or the receiver did not answer); run_query:other_repository; run_query:unsupported:<name>;
    coordinate_not_served.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: while the guard is on, every local launch on the default runner, of every kind (engine run,
      conversation turn, workflow step), starts its heartbeat child and executes its engine only after the
      trusted wrapper has audited its descriptors (AC2) and, after release, installed one Landlock ruleset
      that denies read file and every write right (write, truncate, make, remove, refer) beneath the store
      directory, the real directory of the database the receiver opens, and grants them elsewhere by
      control_clone's ancestor-chain rules; the receiver records store_guard pending at acceptance and
      applied only after the success byte; a probe, create, add or restrict failure ends the launch with
      unavailable_service:confinement:store_guard:enforce:<step>, no heartbeat child and no engine.
      Connecting to the existing authority socket stays possible and is refused without a member
      signature, as today. A guarded payload cannot reach the unconfined receiver's descriptors or memory.
      Exceptions, stated: no direct entry changes in the store directory's ancestors, files created there
      after start unreadable, listing, stat, chmod and execute not covered, no mounting. Set: real
      contained launches of each kind with a fixture engine and a descendant, each trial separate: open
      read and open write of the database and its actual sidecars, read-only open with truncate,
      truncate, unlink, rename out, link out, create a file, a directory, a symlink and a socket inside,
      open authority.lock read-only, unlink, rename out and link out of authority.sock (an ordinary open
      of authority.sock is not a trial: it fails with ENXIO even unguarded and is no evidence for
      Landlock), move and replace the store directory both ways, open through an outside symlink
      pointing in; compatibility assertions in both modes: connect to the running authority socket and
      its unsigned-request refusal; allowed
      worktree, home and temporary writes; an entry created directly in the state root; a
      write-only-ruleset control with no competing lock holder; probe, create, add and restrict failures
      each injected by an argument-matching seccomp filter on the wrapper (the create filter refuses
      landlock_create_ruleset only with flags 0 and an attribute, so the version query passes; the probe
      filter refuses only the version query); receiver /proc/PID/fd and /proc/PID/mem, process_vm_readv
      and writev, and pidfd_getfd where supported, with an unguarded control. Separately, a primitive
      control_clone ruleset test outside the launch preflight shows that following a symlink inside the
      denied directory that points out reaches its target; production refuses that layout (AC3).
      Completeness: rows launch/guard-default, ruleset/primitive-symlink-out, launch/guard-read,
      launch/enforce-fail, launch/ack and launch/receiver-memory require every refusal with its errno
      class (EXDEV or EACCES for link and rename), every allowed operation, the authority socket's
      unsigned-request refusal, the ancestor refusal, the control's flock, no flock trial counted after a
      refused open, pending then applied in the event sequence and no applied event before the success
      byte, the step named and no payload marker after each injected failure, each receiver-access denial
      with its unguarded control succeeding (or the other denying layer recorded and the case not
      counted), and the protected logical state and database bytes unchanged across a quiesced attack
      interval, authorized receiver writes accounted separately.
    falsified_by: >
      Remove the ruleset from the wrapper. Registered mutants: store359-guard-skipped fails
      launch/guard-default, launch/enforce-fail and launch/receiver-memory (each listed content and name
      trial, none of which fails unguarded, succeeds and the payload runs; the socket connect and
      unsigned refusal hold in both modes); store359-write-only-guard fails launch/guard-read;
      store359-ack-early fails launch/ack (an applied event before the success byte).
  - id: AC2
    text: >
      Claim: while the guard is on, the wrapper audits every open descriptor once, immediately after
      parsing its held configuration and heartbeat arguments and before any write or read on a standard
      descriptor or protocol channel (the missing-executable output, the identity line and the release
      read included), and refuses the launch with no heartbeat child and no engine when any descriptor,
      standard streams and protocol channels included, has the device and inode of the store directory or
      of an entry beneath it, or a procfs link (deleted marker removed) naming a path beneath it, or when
      the enumeration, the inspection of any live descriptor or the listing of the store directory fails.
      The check is by identity and path, never by type, so an ordinary file outside the store on stderr
      passes. On a refusal it writes the failure byte with step audit only to the setup pipe, and only when
      that pipe passed the audit; otherwise it exits without writing, with a dedicated exit status; it
      never writes to a forbidden stream. Because this failure precedes the identity line, the receiver
      handles it on an explicit pre-identity path: when reading the identity line fails, and before
      classifying the failure, it inspects the setup pipe and reaps the wrapper within the existing
      bounded identity deadline; a failure byte with step audit records enforce_failed with step audit;
      no byte with the dedicated audit exit status records enforce_failed with step audit, unreported;
      anything else keeps today's generic containment error. It never releases a worker without a valid
      identity, never reads a forbidden child standard stream to obtain an audit report, and keeps
      today's containment cleanup. The post-release reader gains the failure byte for the later steps;
      the post-release success acknowledgement is unchanged. The existing close_fds spawn and heartbeat
      sanitation are unchanged. Set: at the real
      wrapper spawn, early cases: stdout and stderr each a writable store database handle, stdin a store
      file, the setup pipe replaced by a store handle, and stderr an ordinary log file outside the store;
      leaked cases with clean standard streams and channels: an extra inherited writable sidecar, a
      read-only authority.lock, the store directory and a deleted store file, each used by the fixture
      payload when not refused; an uninspectable descriptor; an unreadable enumeration; a clean launch.
      Completeness: row launch/descriptors-early requires each early case refused with fixture bytes
      unchanged, no release read from the forbidden stdin, no output on a forbidden stream, the report on
      the setup pipe only when it passed, the final receiver launch record for each early case
      (enforce_failed with step audit, or audit unreported when the setup pipe was the forbidden one,
      never the generic containment error, no release, containment cleaned up), and the ordinary log
      file launching; row
      launch/descriptors-leaked requires each leaked case refused before the heartbeat, no helper or
      engine holding the handle, each inspection or enumeration failure refused, and the clean launch
      applied.
    falsified_by: >
      Registered mutants: store359-fd-check-late (the audit moved after the identity line and the release
      read) fails launch/descriptors-early (the identity line lands in the fixture database and its bytes
      change); store359-audit-late-reader-only (the failure byte read only by the post-release reader)
      fails launch/descriptors-early (the record shows the generic containment error instead of the
      required guard outcome); store359-fd-check-skipped fails launch/descriptors-leaked (the payload
      uses the extra inherited handle).
  - id: AC3
    text: >
      Claim: while the guard is on, the receiver refuses a local launch, default or risky, before
      acceptance with no worker spawned, by name with the resolved path and the fix: when a structured
      Landlock probe reports unsupported_platform, landlock_disabled, syscall_missing, syscall_blocked or
      abi_below_3 (control_clone.abi unchanged); for a risky launch also when the platform is not x86_64
      or the ABI is below 6, mirroring the runner's own floor, which stays; when the configured store path
      does not resolve to a regular database file in a directory owned by the account; when any entry
      beneath that real directory, listed recursively without following links, is anything other than a
      directory or a regular file with link count 1, except exactly the entry authority.sock directly in
      the store directory, which may be a socket owned by the account with link count 1, bound or stale;
      when the receiver's own mountinfo, with filesystem roots translated per device, shows a second
      mount exposing the directory, an ancestor or any file or subtree in it, or cannot be read; when the
      runs root or the run's directories fall inside the directory; or when a required launch location
      (worktree, its gitdir and Git common directory, home, temporary and runtime directories, runs root,
      client state, risky scratch parent) equals or lies beneath the directory, or the directory lies
      beneath one of them. The socket exception adds no filesystem grant. A symlinked path to the store
      directory is followed, not refused. Remote launches are not checked. Set: ENOSYS, EPERM and
      EOPNOTSUPP from real seccomp filters on the receiver, ABI 1 and 2 and an unsupported platform by
      probe parameter, for both kinds; risky ABI 3, 4 and 5 and a non-x86_64 platform by probe parameter;
      ABI 3 and the host's ABI for default, the host's ABI for risky; a normal running factory layout with
      an actually bound authority.sock and an ordinary receiver launch completing while the authority
      serves; a stale authority.sock; an unexpected socket elsewhere beneath and one under another name;
      a FIFO; a device where the fixture can make one; a symlink; a symlinked sidecar of a custom
      database name; a hard-linked file beneath; hard links to the database, a sidecar and the lock; a
      directory bind, an ancestor bind and single-file binds of the database and the lock in the actual
      enforcement namespace; unreadable mountinfo; the runs fallback with neither runs nor state_root; an
      explicit runs outside the store with no state_root; a worktree under the store directory; a store
      under the worktree, the Git common directory, home, temporary and runtime directories, and equality
      cases; an external client state place overlapping it; a risky worktree or scratch parent that is an
      ancestor of it; a symlinked path to a valid store directory; an absent optional tool root; the
      fallback with the marker present. A probe parameter reaches only the receiver's criterion: the
      wrapper probes the real kernel again and control_clone.confine and the risky runner keep their own
      floors, so the distinguishing failure of a skipped receiver check is acceptance, and on an actual
      ABI-2 host acceptance followed by enforce_failed with no payload. Completeness: rows launch/abi,
      layout/entries, layout/mounts and
      layout/placement require each refusal by name with no worker, each accepted control launching, the
      fallback with the marker launching on its old path, and a missing mount or device facility recorded
      NOT RUN, which never satisfies those cases.
    falsified_by: >
      Registered mutants: store359-low-abi-accepted (a default launch at parameter ABI 2 is accepted;
      on an actual ABI-2 host it is accepted and then ends enforce_failed with no payload) and
      store359-risky-floor-skipped (a risky launch at ABI 5 by parameter is accepted) fail launch/abi;
      store359-socket-exception-removed fails layout/entries (the normal running factory launch is
      refused); store359-special-entries-allowed fails layout/entries (the unexpected socket and the FIFO
      are accepted); store359-links-allowed fails layout/entries (the hard links are accepted);
      store359-file-binds-allowed fails layout/mounts; store359-placement-skipped fails layout/placement
      (the runs fallback is accepted and the engine then fails reading its configuration).
  - id: AC4
    text: >
      Claim: a risky launch adds no layer before the confined runner, and while the guard is on it is
      accepted only when the actual grants the runner will emit for this launch neither equal, lie
      beneath, nor contain the store directory, and no copy source resolves into it. The census keeps
      three sets apart. (a) Placement and source-expansion inputs, which are not grants: the selected
      client's places (environment or configured default), used only to expand the client's source
      entries, and the scratch parent, below which a fresh scratch directory is made; these are judged
      only by AC3's conservative placement checks, and a place contributes to grants only through the
      source entries that use it. (b) Actual post-preparation grants, computed as data from the same
      configuration file and environment handed to the runner, on the same prepared configuration,
      including the implicit exclusions (deny_read extended with borrow_root and every client's
      credential sources): the grants grants_for emits after expansion, symlink resolution and its
      deny_read filter (an item beneath an exclusion contributes nothing; an ancestor of one contributes
      its non-symlink children recursively), from read roots, installed tools and PATH entries, the
      worktree, runner checkout and scratch placeholders, project roots and resolved targets of existing
      read_link sources, the configuration file, the shared and private Git common directories, write
      roots and Git write grants; the resolver directory resolver_grants adds; and client state grants as
      qualified state_grants would emit them (none for an absent home place; entries not yet existing
      represented at the path the runner would create; an entry the runner's qualification would refuse
      is not a grant, and one overlapping the store directory refuses the launch as store_reachable). The
      fresh scratch directory has one symbolic identity in both computations, and its parent is never
      compared as granted. The preflight is read-only: it never calls the mutating state preparation.
      (c) Copy sources: general seeds, client seeds and credentials, judged separately and without the
      exclusion. Absent optional items behave as in the runner; an unresolvable required item refuses
      before acceptance. The receiver records pending with precondition_checked at acceptance and
      runner_started on the success byte, never store_guard applied. A gate parity check compares only
      set (b), normalized by path and rights, with the grants the runner actually emits from grants_for,
      resolver_grants and qualified state_grants, and fails on a difference in either direction. Set: a
      real risky launch with the shipped configuration and the installed namespace helper; exposure
      fixtures on otherwise valid grant or copy configurations that pass every placement check: a read
      root containing the state root without an exclusion, a client read_link resolving into the store,
      a configuration file inside it, a general seed, a client seed and a credential source resolving to
      store files; for each, a companion run of the unchanged runner without the census showing it grants
      or copies that route; an early-refusal timing fixture: an unresolvable required root; accepted
      controls: an absent optional root, a broad read root with deny_read on the store directory, an
      unused client place, and a client place whose selected sources are all disjoint from the store;
      component census tests without a launch for the routes placement refuses end to end (worktree and
      scratch-parent ancestors, Git common directory, client state place overlap); parity fixtures
      including the shipped Claude and Codex configurations, the credential exclusions, an absent state
      home and newly created state entries. Completeness: row launch/risky-real requires the payload's
      completion and its refusals on the store and the lock; row launch/risky-census requires the named
      refusal before acceptance with nothing spawned for each exposure fixture and for the unresolvable
      root, each companion showing the route reachable, every accepted control launching, each component
      case refused, and set (b) parity with the runner on each fixture on which the runner's grant preparation succeeds; for the unresolvable root and any component fixture whose unchanged runner qualification refuses, the expected refusal outcome instead of a grant set.
    falsified_by: >
      Registered mutants: store359-guard-before-runner fails launch/risky-real (a launch that otherwise
      completes never reaches its payload); store359-precondition-skipped fails launch/risky-census (for
      each exposure fixture the payload reads a planted sentinel through that route, or the seed copy
      exposes it; for the unresolvable required root the launch is accepted and then fails in the runner
      with no payload, which is a timing failure, not an exposure); store359-census-prefilter (configured
      roots compared instead of actual grants) fails launch/risky-census (the broad read root with a
      working exclusion is refused); store359-census-places-as-grants (client places treated as grants)
      fails launch/risky-census (the unused-place or disjoint-place control is refused, or parity fails).
  - id: AC5
    text: >
      Claim: while the guard is on, a launch whose engine is Codex runs with sandbox_mode
      danger-full-access applied after and over the role's and account's settings, approval policy
      unchanged, only on launches whose sampled guard decision is on, so Codex never runs with its sandbox
      off and without the ruleset, and its sandbox is never switched off as an enforcement-failure
      fallback; with the switch off the role's setting stands; and the pinned Claude Code's ordinary Bash
      tool works under the ruleset. The receiver's trusted Codex preflight invocations are not counted as
      evidence. Set: pinned real Codex through the production default wrapper with a workspace-write role,
      running a native shell command and a child that write the worktree and try the database, a sidecar
      and the lock; the same through a real risky launch; an injected enforcement failure; the same role
      with the switch off; pinned Claude Code running its Bash tool and an ordinary build step; the
      heartbeat setup deadline. Completeness: row launch/engines requires the runtime identity and
      effective setting recorded, the tool executed, the worktree write, each store refusal with errno,
      unchanged protected state, no Codex after the enforcement failure, the role's setting with the
      switch off, Claude Code's tool success, and the deadline met. A model reporting that it cannot is not
      evidence.
    falsified_by: >
      Registered mutants: store359-role-sandbox-wins fails launch/engines (the shell command cannot
      start); store359-guard-skipped on a disposable fixture store fails it (the command writes the store).
  - id: AC6
    text: >
      Claim: while the guard is on, inside a default run, control_eligibility.entry_gate in an enrolled
      workspace with no wired gate returns a remote gate over the endpoint its receiver made and readied
      before acceptance, never opening the store; a wired gate passes through unchanged. The remote gate
      holds exactly domain_uuid, repository_uuid and authority_generation from the receiver's verified
      binding, SCHEMA, decide(station, unit, context, ticket) including coordination,
      decision_blockers(unit, references), completion(unit) returning exactly the four facts with all
      false for a unit with no subject, landed(unit) derived locally from completion, floor_entry(unit,
      word, landed), replication_status(), local observe, close, refusal_types and refusal_code; any other
      attribute raises run_query:unsupported:<name>, also an AttributeError; a workspace whose binding
      names another repository stops run_query:other_repository. The receiver applies Gate semantics
      unchanged, including ticket checks and staleness, on its own binding, workspace and trust; checks
      scope per operation (an existing unit of a work question must be an execution unit of the launch
      repository; an existing unit of a coordination question must be a pm_cycle of the launch domain and
      repository; otherwise coordinate_not_served; a missing one gets the direct Gate's own answer); and
      returns each decide and decision_blockers answer with the events its Gate emitted for that request
      (station decision, decision_dependency, invalid_record) limited to the frozen event fields, which
      the client delivers in order to its local observe. Responses hold only the frozen fields: identity
      metadata, no record bodies, membership bodies, keys or journal rows; the replication projection is
      stated to be store-wide, including pending command identities. Status asks replication_status when
      its override resolves to the receiver's database and reports any other override inside the store
      directory as not present before any open. Each request is one bounded read transaction on a serving
      thread with its own read-only connection opened in that thread. The endpoint is removed by the
      receiver at run end and by the Runner after observing the receiver's exit; no connection-based
      sweep at receiver start; a failed or absent receiver is unavailable_service:run_query, never a direct
      open. The query server never opens dispatches or launches anything. Set: an enrolled journey under
      the real ruleset through run-check, bundle and hash to the build, frontier claimable and withheld
      with offers, observations and handoff records, plan references, executor context, tickets and a
      stale ticket, work_state.completion_view with the remote gate, a valid coordination decision, a
      stale coordination ticket, a missing cycle, a missing dependency, status in both modes; the same
      questions of a direct Gate at the same state with callbacks recorded; a committed store change
      between two requests; another repository's execution unit, a member id as unit, a foreign
      reference, another repository's pm_cycle, an execution unit passed to coordination, an unlisted
      request, another checkout's workspace; two concurrent runs in different repositories; endpoint
      creation and readiness failures; a killed engine; a killed receiver; receiver A paused between bind
      and listen while receiver B starts; a leftover endpoint of a dead receiver and Runner. Completeness:
      row query/journey requires the build reached, stable semantic fields and local callback events
      equal to the direct Gate's in order with decision ids and clock fields normalized, the missing
      cycle and dependency answered as a direct Gate does, zero attempted direct store opens including on
      timeout and transport failure, and the fresh answer after the change; row query/scope requires each
      named refusal, exactly the frozen fields with all approved metadata present, no planted sentinel and
      each run its own answers; row query/lifecycle requires refusal before acceptance on creation or
      readiness failure, the endpoint gone after each end within its deadline, A's endpoint surviving and
      answering, and the leftover endpoint affecting no later launch.
    falsified_by: >
      Unset VELDO_RUN_QUERY in the engine environment: query/journey stops unavailable_service:store.
      Registered mutants: store359-events-dropped fails query/journey (callback events differ);
      store359-query-any-unit (a foreign unit's projected identity appears in an answer) and
      store359-query-fallback (a direct open attempted, even if caught) fail query/scope;
      store359-query-leak (no removal at run end) and store359-query-startup-sweep (a connection-refused
      sweep at receiver start removes A's endpoint) fail query/lifecycle.
  - id: AC7
    text: >
      Claim: the guard is ON by default, and the PRESENCE of store-guard.off in the store directory turns
      it OFF; deleting it turns the guard back ON. Exactly: a regular file named store-guard.off, not a
      symlink and owned by
      the account, in the store directory resolved for enforcement, read by no-follow metadata, turns this
      whole specification off for every local launch that starts while it is present (no ruleset, no
      preflight, no census or risky floor, no VELDO_RUN_QUERY, the role's Codex sandbox setting); absence
      means on; any other entry at that name or a failed check other than absence refuses
      invalid_input:layout:switch, never reading as off; the receiver samples it once per launch and every
      later step uses that sample; its contents and mode carry no meaning; launch code never creates or
      deletes it; launch lines and records show pending then applied or enforce_failed for guarded
      launches, and off with the marker path or refused with reason and fix immediately; the status
      command shows on, OFF with the marker path and time, or invalid, as the configuration for later
      launches, never as a claim about runs in progress; a guarded or risky run cannot directly create the
      marker, link or rename a file to its name, or replace the store directory or its parent. Changes
      affect later launches only; deleting the marker does not confine runs started while it was present.
      Set: a valid marker on a valid layout; a valid marker on a fixture with ABI forced to 2 and an extra
      hard link; the marker removed on that defective fixture; the marker removed on a valid fixture;
      symlink, directory and foreign-owner markers; a mode and a content change of a valid marker; inside
      a guarded run and a risky run, create, link to, rename to, and replace of the directory and its
      parent; off to on with one surviving unguarded and one surviving guarded run, and on to off with a
      surviving guarded run. Completeness: row switch/off requires the fixture opening the store, no query
      variable, the role's setting, off with the path on the record and OFF in status for the valid
      marker; today's launch on the defective fixture with the marker; the named refusal on that fixture
      without it; a guarded launch on the valid fixture without it; each invalid marker refused by name;
      the mode and content changes without effect; row switch/run-cannot-flip requires each attempt
      refused and the next launch guarded; row switch/transitions requires status showing on, the next
      launch guarded, the surviving unguarded run still reaching the fixture store and the surviving
      guarded run still refused, and on to off leaving the guarded run guarded.
    falsified_by: >
      Registered mutants: store359-switch-ignored fails switch/off; store359-switch-outside (the switch
      read from a run-writable location, which the guarded payload then changes) fails
      switch/run-cannot-flip (the next launch is unguarded).
required_evidence: [unit, integration]
rollback: >
  The guard is ON by default; the presence of store-guard.off in the store directory turns it OFF. To
  roll back operationally, create store-guard.off (a regular file) in the store directory: every later
  local launch takes today's path, and launch records and status show it. Deleting the file turns the
  guard back ON for later launches. Runs already guarded stay guarded until they end. For a
  full rollback, revert the change. The store's format, the lock file, the authority socket and the
  journal are untouched; query endpoints under the runtime directory are removed with their runs, by the
  Runner, or with the runtime directory.
---

## Intent

Agent runs, which execute model-chosen commands, cannot read or write the Veldo store. Today a default
factory run has no filesystem confinement (control_launch.py:401 to 420, 476, 3168 to 3190). After this
change one Landlock ruleset, installed by the trusted wrapper, denies every default run content and name
access to the store directory; risky runs keep the confined runner's allowlist, whose effective grants the
receiver checks cannot reach it; and the commands a run uses for store answers ask the run's own receiver.
The guard is ON by default; the presence of a visible file, store-guard.off, in the store directory turns
it OFF, and deleting that file turns it back ON.

## Context

Owner approval: Telegram 42856 and 42864 ("Yes build it"), narrowed by 42876 to 42878 to the run
boundary only, recorded as 2026-11-21-veldo-store-write-lock in the owner's approvals, section "Scope
narrowed". Design: research design veldo-store-write-lock-2026-11-21 (design.md, revision 6), after five
independent validations whose findings are answered in revision-notes.md.

Dropped by the owner's decision and not part of this specification: the authority.lock capability check
in open_store and every change to how Veldo's own processes open the store (writer migration, signer
relay, lock-first setup, layout checks at authority start and in setup, the write census). VELDO-0113's
contract-gap row stays a GAP row. The authority socket is not moved and its authentication is unchanged.

Reused, not invented: control_clone's Landlock rules and confine (VELDO-0042); the contained wrapper and
its setup status byte (VELDO-0039, VELDO-0040, VELDO-0041); the confined runner and its allowlist
(VELDO-0208); the eligibility Gate and entry_gate (VELDO-0052); the pinned engines (VELDO-0127).

Verified facts the design rests on: a Landlock-restricted task cannot mount, so no layer precedes the
risky runner and default runs lose mounting; with read allowed a run could flock the lock, so runs get no
read path; Landlock does not revoke an already open descriptor, so the wrapper audits descriptors before it
uses any of them; Landlock attaches rules to the resolved directory, so a symlinked path to the store
directory is covered while a symlinked or hard-linked entry inside it is not; connecting to a pathname
socket is not a Landlock filesystem right, so the authority socket stays reachable as IPC and must be
allowed by the entry check; the runner's grants are post-exclusion; Codex 0.166 always uses bundled
bubblewrap for its own sandbox; a client place only expands sources and the scratch parent is never
granted, so neither is itself a grant; opening a pathname Unix socket fails with ENXIO even without
Landlock.

Lead decisions: Codex runs with its own sandbox off inside a guarded run (AC5), selected only from the
launch's sampled guard decision. The switch's polarity is the decided rule and is not changed: the guard
is ON by default, the PRESENCE of store-guard.off in the store directory turns it OFF, and deleting it
turns the guard back ON (AC7).

Old kernels: launches are refused below ABI 3 (AC3) rather than run and warn; risky launches are refused
before acceptance below the runner's own floor (x86_64, ABI 6), which they fail today after acceptance.
Refusal costs availability on such hosts; it is chosen because warn-and-run leaves the protection
silently absent and needs a second Codex path, and the owner's deliberate, visible recovery is the
marker. This host is at ABI 8 on x86_64.

Amendments. VELDO-0254 AC3: while the guard is on, default runs lose access to the store directory,
direct entries in its ancestors and the ability to mount; local launches are refused below Landlock ABI
3, on an aliased or misplaced store layout and on a runs directory inside the store directory; a risky
launch is refused below the runner's own floor, or when its runner's effective grants or copy sources
reach the store directory; Codex's own sandbox is off inside guarded runs.

## Behavior changes the owner sees

While the guard is on (none of these with store-guard.off present):

- Runs cannot read or write anything in the store directory.
- Default runs cannot mount: bubblewrap, rootless podman or buildah, unshare with mounts, Codex's own
  sandbox and Claude Code's optional sandbox fail inside them.
- Codex runs with its own sandbox off inside guarded runs, over any role setting.
- Default runs cannot create, remove or rename entries directly in the store directory's ancestors.
- Local launches are refused below Landlock ABI 3 or when Landlock is disabled, blocked or unsupported;
  risky launches below ABI 6 or off x86_64 are refused before acceptance instead of failing in the
  runner.
- Local launches are refused on a store directory holding a symlink, a special file other than the
  authority's own authority.sock, or a multiply linked file, on an extra mount of it, on a runs directory
  inside it (no `runs` and no `state_root`), or on a store beneath a location runs need (home, temporary,
  runtime, worktree, Git directory, which includes the conventional Git-directory store).
- A risky launch is refused when its runner's effective grants or copy sources reach the store directory.
- Plan run-check, frontier, the completion view and status inside a default run answer through the
  receiver; any default run can also ask other live receivers for their status answers, and the
  replication part is store-wide.
- Launch lines show pending at acceptance, then applied or enforce_failed; off and refusals show at once.
  The status line shows the configuration for later launches; a present but invalid marker refuses
  launches until fixed.

Not changed: how the authority, setup, maintenance commands, the CLI, the API process and the signer
open the store; the authority socket.

## Out of scope

- Everything dropped by the owner's decision (see Context).
- Any process of the owner's account outside a Landlock domain, including Veldo code.
- A run that recruits an unconfined same-account process (including to create the marker), or a risky run
  that recruits an authenticated TCP service; descriptors such a service sends later.
- A run's chmod of store entries, its view of their names, sizes and times, its connection to the
  authority socket (refused without a member signature), and signals.
- Store answers for risky runs (no Unix sockets); their enrolled gate stops by name as today.
- Caller isolation between runs on the query endpoints.
- A migration procedure from the conventional Git-directory store to a factory layout.

## What the reviewer judges

- Normal use: on this Linux host with a factory store and a serving authority, factory runs start
  through the receiver, are guarded, and a planned run's run-check, frontier and status answer through
  the receiver; Veldo's own processes behave exactly as before; creating store-guard.off restores today's
  launches and is visible.
- Threat model: an agent run's own processes executing model-chosen commands. Not defended: the owner's
  account acting outside Landlock, recruitment of unconfined services.
- Out of review scope: edge cases unlikely in normal use (Telegram 28962), planted files in the installed
  directory, deliberately forged records, resource exhaustion by the owner's own account, and a reported
  adapter whose transport points back at this host.

## Notes

- Exactly one new enforcement mechanism: the default-run Landlock ruleset. Risky runs get no new layer.
- The marker lives in the store directory because no guarded or risky run can directly create, link or
  rename an entry there.
- The entry check's only special-file exception is the authority's own socket at its derived path; any
  further normal entry B0 finds must be named here before B2.
- The real-launch rows need the systemd user manager and the installed namespace helper, so the new suite
  is listed in scripts/gate_unconfined.json, the one protected path, approved at landing.

## History

2026-11-21: draft from the design, after the owner's approval of the direction (Telegram 42864).
2026-11-21: revision 2 after the first validation.
2026-11-21: revision 3, narrowed to the run boundary by the owner's decision (Telegram 42876 to 42878).
2026-11-21: revision 4 after validation-narrow: presence-means-off switch kept by lead decision with
invalid-marker refusal, single sampling and owner-visible state; effective-grant census for risky runs;
full remote gate contract with references, context, tickets, frozen schemas and a replication projection;
store directory from the opened database with a recursive entry check; runs-location and placement
checks; descriptor audit before the heartbeat; ABI check for both local kinds with a structured probe;
query endpoint before acceptance with defined cleanup owners; corrected falsifiers.
2026-11-21: revision 5 after validation-narrow2: the authority's own socket allowed by exact name in the
entry check; completion, coordination scope, forwarded events and fully frozen schemas in the remote
gate; the descriptor audit before any use of a standard descriptor; no connection-based endpoint sweep,
a ready endpoint before acceptance; pending then applied on records; the risky floor before acceptance;
post-exclusion census grants; falsifiers bound to reachable behavior.
2026-11-22: revision 6 after validation-narrow3: switch polarity restated unchanged (ON by default,
presence of store-guard.off turns it OFF); the risky census separates placement inputs, actual grants and
copy sources, with set-(b)-only parity; an explicit receiver pre-identity path for an early audit
failure; socket-open, unresolvable-root and low-ABI rows corrected to outcomes their fixtures can produce.
