---
schema: veldo.plan/v1
id: PLAN-0019
title: Dark Factory project coordination inside Veldo
kind: mvp
status: ready
revision: 3
owner: dmitry
approved_by: dmitry
approved_at: 2026-09-22
risk: critical

outcomes:
  - id: O1
    becomes_true: >
      Project owners can trace an accepted objective through deliberately admitted work and give a
      version-bound decision on the enrolled input surface where they are working.
    measure: >
      Every admitted item resolves to its owner, accepted request and priority; concurrent answers
      from enrolled channels produce one attributable settlement with the exact presentation
      receipt.
  - id: O2
    becomes_true: >
      Operators can restart or replace the authority without repeating an uncertain effect or losing
      acknowledged history.
    measure: >
      Real-process boundary crashes, replica restoration, and the combined scope-change and lost-
      effect-acknowledgement journey produce verified recovery or a named authority stop; no
      acknowledged command lacks its durable off-host export.
  - id: O3
    becomes_true: >
      Builders and reviewers can rely on completion meaning verified, independently reviewed,
      authorized publication of the exact candidate and accepted outcomes.
    measure: >
      The installed floor slice lands successfully; red gates, rejected approvals, stale
      dependencies, missing regression receipts, and build-only attempts cannot establish
      completion.
  - id: O4
    becomes_true: >
      Project owners can delegate bounded coordination and engineering to qualified workers without
      granting models admission authority or unlimited cost and process lifetime.
    measure: >
      Every supported engine and host profile passes containment, stopping, credential, accounting,
      and revocation qualification; repeated graphs and deleted checkpoints cannot repeat a
      committed effect or change authoritative decisions.
  - id: O5
    becomes_true: >
      Adopters can install the same governed factory from every composed pack and recover with a
      compatible previous release.
    measure: >
      Every installed pack runs the first slice and migration, clone replacement, host-loss,
      corruption, and rollback qualification using its declared inventory.

non_goals:
  - id: NG1
    text: >
      No Kafka, Redis, Temporal, Kubernetes, second database within a coordination domain,
      microservice decomposition, LangGraph server, automatic host failover, or cross-repository
      execution transaction.
  - id: NG2
    text: >
      No customer charging, production deployment, telecom operations, or integration with another
      operator.
  - id: NG3
    text: >
      Amended 2026-09-22 by owner Telegram 28857: the prohibition on a new management console
      is removed. Veldo\'s own phone and desktop UI is in Release 1. Unverified Jira board
      changes, modifications to published prose and client-engagement material remain excluded.

constraints:
  - id: C1
    text: >
      The controlling design is docs/design/PLAN-0019-dark-factory-design.md, R01 through R76. The
      project layer lives in this repository. The separate-repository rule, single-operator
      restriction, terminology ban, and fixed fifteen-role roster do not apply under Dmitry's
      rulings. Draft artifacts neither approve this plan nor activate runtime changes.
  - id: C2
    text: >
      Decision records precede executable changes to process ownership, persistence, replaceable
      LangGraph execution, and review and completion semantics. VELDO-DEC-0003 and VELDO-DEC-0004
      frame placement and process retirement. Effective architecture revisions, policy loading,
      capability declarations, and real containment failure tests must replace no_detached_processes
      and agent-mediated launch for the governed project runner; extending the lexical ban to reject
      that runner is prohibited.
  - id: C3
    text: >
      The 2026-09-17 D1-D4 rulings on VEL-18 remain historical decisions. Amended 2026-09-22 by
      owner Telegram 28848: Release 1 accepts local committed authority results; off-host
      acknowledgement before mutation success, dispatch or dependent publication moves to Release 2.
      Remote Git confirmation still precedes source completion. Linux authority, isolated clones and
      C13 attachments remain. The Mac worker is added by 28852; it is not a replica or replacement
      authority.
  - id: C4
    text: >
      R21 permits one local SQLite authority at <git-common-dir>/veldo/control/control.sqlite3 per
      domain on a qualified local filesystem. LangGraph owns only isolated checkpoint tables; model
      processes receive no database access. Cross-namespace writes and indirect writes refuse, and
      domain history remains valid when checkpoints are removed.
  - id: C5
    text: >
      Amended 2026-09-22 by owner Telegram 28848: install and qualify only the assets needed by the
      running journey, including a compatible isolated pinned, hashed and licensed LangGraph
      runtime. The full distribution inventory and every-pack qualification move to Release 4. R35
      stdlib_only_enforcement remains for validators, authorization, gate imports, journal replay
      and recovery. No persistent graph checkpointer is required in Release 1; VELDO-0044 moves to
      Release 2.
  - id: C6
    text: >
      R53 places implementation in canonical engine/ with byte-identical pack synchronization.
      Domain contracts accept plain versioned data and import neither LangGraph nor worker engines.
      Only the store commits, the runner launches, the lander publishes source, and the Evidence
      Service signs observations. Every asset has an explicit distribution disposition.
  - id: C7
    text: >
      Amended 2026-09-22 by owner Telegram 28857 and 28859: new work starts only with a Telegram
      message or authenticated API call, including the UI message box. Both use one intake path;
      arbitrary message text is permitted. Agents may fetch a referenced Jira ticket using their
      configured tools. Nothing watches Jira and no special Jira intake or decision channel is
      built. Telegram and authenticated UI/API decisions share one authority settlement with exact
      presentation and originating actor evidence. Additional channels are Release 4 candidates, not
      enrolled by this plan.
  - id: C8
    text: >
      Every enrolled channel edge has its own restricted signing key and canonical attribution
      evidence. Chat binds platform message ID, sender ID, and timestamp pulled from the platform,
      never text alone. Channel-specific enrollment and sandbox proof precede activation;
      independent principal quorum cannot be inflated through several channels.
  - id: C9
    text: >
      Existing WARP and VELDO identities remain unchanged. New durable identities separate aliases,
      UUIDs, schema versions, concurrency versions, and plan scope revision. This draft allocates
      aliases from the inspected specs/ maximum as expressly requested; runtime concurrent
      allocation is implemented later under R73.
  - id: C10
    text: >
      Amended 2026-09-22 by owner Telegram 28848: VELDO-0032, VELDO-0033 and VELDO-0034 clock
      reporting, refusal propagation and display qualification move to Release 2, removing the
      B-before-C prerequisite. Preserve VELDO-0015's existing detector and stand-down. Release 1
      callers must surface a named uncertainty stop and never reinterpret it as contention or
      permission to land.
  - id: C11
    text: >
      Each implementation item still requires a ready specification, three or four falsifiable
      criteria, proof, independent review and a green gate. This revision changes scope, never
      specification status or historical proof. Release 1 qualifies real Claude Code and Codex
      workers, real Telegram and authenticated UI/API decisions, and the full installed journey.
      Fixtures prove only their named consumption checks; recovery and interrupted-settlement
      qualification are Release 2. Source landing does not activate a service or channel.
  - id: C12
    text: >
      Amended 2026-09-22 by owner Telegram 28852: Release 1 qualifies this Linux box and a Mac
      worker host. Authority stays on Linux; Mac workers use the built VELDO-0108 authenticated SSH
      relay. macOS and iOS requirements route only to a qualified Mac. Linux uses systemd/cgroup v2;
      the Mac has its own simple launch, cap, stop and exit profile without cgroups. Cloud and other
      host profiles move to Release 4; no profile activates merely by being named.
  - id: C13
    text: >
      Dmitry's 2026-09-17 ruling on D4: a worker reads other repositories
      only through attachments its contract names, each pinned to an exact accepted commit and
      provisioned read-only from the shared object cache; it cannot reach a repository the
      contract did not name and cannot write to an attached one. A write to another repository is
      its own unit, admitted in that repository's own domain and linked here by a dependency.
      An interactive session run by a person is not a worker and is not confined by this plan.

  - id: C14
    text: >
      Owner Telegram 28848, 2026-09-22: 'Claude code and langgraph can't be out.' Release 1 is every
      function of the running dark factory journey. Recovery, robustness, durability and scalability
      are later; neither worker engine nor the LangGraph step runtime (R34) may be cut.
  - id: C15
    text: >
      Owner Telegram 28859, 2026-09-22: each role's versioned capability configuration defines
      exactly the MCP servers and tools handed to its worker. The factory must not silently remove,
      replace or add capabilities available in that configuration. Unsupported handoff refuses
      visibly; no factory-specific Jira channel is needed. Existing scope, credential custody and
      C13 repository boundaries still apply to authorized use.
  - id: C16
    text: >
      Owner decision 2026-09-22 after stack comparison (UI requirement in Telegram 28857): Veldo
      uses React, TypeScript, Vite, shadcn/ui including its AI chat parts, TanStack Table, React
      Flow and Monaco. No Chinese-origin dependency anywhere and no library with free and paid
      tiers. Verify provenance, transitive dependencies and licensing before selecting exact
      versions; a conflicting component requires an owner decision, not an exception hidden in
      implementation. Every screen must be excellent on phone and desktop. Bcengi products remain on
      Vue.
  - id: C17
    text: >
      Owner decision 2026-09-22: the UI and other callers use an authenticated API to read state,
      send messages and answer version-bound decisions. A versioned workflow definition lives in
      Veldo and is executed by LangGraph. The workflow canvas edits that definition and never
      executes it or grants admission. UI/API sessions identify the actual enrolled principal;
      supplied actor text is never authentication.

feature_tree:
  - id: F1
    title: Package A - Ratified boundaries and executable contracts
    outcome_refs: [O1, O2, O3]
  - id: F2
    title: Package B - Durable control foundation
    outcome_refs: [O2, O4]
  - id: F3
    title: Package C - Verified and recoverable engineering delivery
    outcome_refs: [O2, O3]
  - id: F4
    title: Package D - Qualified production workers and governor
    outcome_refs: [O3, O4]
  - id: F5
    title: Package E - Decisions at every enrolled input surface
    outcome_refs: [O1, O2]
  - id: F6
    title: Package F - Projects, objectives, grooming, and dependencies
    outcome_refs: [O1, O3]
  - id: F7
    title: Package G - Bounded project coordination and configurable teams
    outcome_refs: [O1, O4]
  - id: F8
    title: Package H - Installable, migratable, and recoverable operation
    outcome_refs: [O2, O5]
  - id: F9
    title: Owner UI and authenticated API
    outcome_refs: [O1, O3, O4]

work:
  - item: W1
    spec: VELDO-0016
    title: Decision records and effective policy amendments
    feature_refs: [F1]
    depends_on: []
    order: 11016
    release: 1
    stage: 1
  - item: W2
    spec: VELDO-0017
    title: Entity identity and lifecycle schemas
    feature_refs: [F1]
    depends_on: []
    order: 11017
    release: 1
    stage: 1
  - item: W3
    spec: VELDO-0018
    title: Release and behavior-floor integration contracts
    feature_refs: [F1]
    depends_on: [VELDO-0017]
    order: 11018
    release: 1
    stage: 1
  - item: W4
    spec: VELDO-0019
    title: Combined dependency graph and decision observation rules
    feature_refs: [F1]
    depends_on: [VELDO-0017, VELDO-0018]
    order: 11019
    release: 1
    stage: 1
  - item: W5
    spec: VELDO-0020
    title: Signing and authority contracts for enrolled channels
    feature_refs: [F1]
    depends_on: [VELDO-0016, VELDO-0017]
    order: 11020
    release: 1
    stage: 1
  - item: W6
    spec: VELDO-0021
    title: Completion and executable eligibility predicates
    feature_refs: [F1]
    depends_on: [VELDO-0018, VELDO-0019, VELDO-0020]
    order: 11021
    release: 1
    stage: 1
  - item: W7
    spec: VELDO-0022
    title: Section 2 admission semantics
    feature_refs: [F1]
    depends_on: [VELDO-0017, VELDO-0020]
    order: 11022
    release: 1
    stage: 1
  - item: W8
    spec: VELDO-0023
    title: Atomic journaled commands and deterministic replay
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022]
    order: 11023
    release: 1
    stage: 1
  - item: W9
    spec: VELDO-0024
    title: Signed Git replication and off-host acknowledgement
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023]
    order: 20024
    release: 2
  - item: W10
    spec: VELDO-0025
    title: Authenticated membership and scoped delegation
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023]
    order: 11025
    release: 1
    stage: 1
  - item: W11
    spec: VELDO-0026
    title: Revocation and authorization rechecks
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0025]
    order: 11026
    release: 1
    stage: 1
  - item: W12
    spec: VELDO-0027
    title: Protected signing and key lifecycle
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0025]
    order: 11027
    release: 1
    stage: 1
  - item: W13
    spec: VELDO-0028
    title: Protected effect execution and atomic nonce consumption
    feature_refs: [F2]
    depends_on: [VELDO-0023, VELDO-0025, VELDO-0027]
    order: 11028
    release: 1
    stage: 1
  - item: W14
    spec: VELDO-0029
    title: One signed enrollment binding decides which authority a clone writes to, and nothing ambient does
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0025]
    order: 11029
    release: 1
    stage: 1
  - item: W84
    spec: VELDO-0107
    title: Local clients reach the authority over authenticated IPC carrying explicit workspace coordinates
    feature_refs: [F2]
    depends_on: [VELDO-0023, VELDO-0025, VELDO-0029]
    order: 11107
    release: 1
    stage: 1
  - item: W85
    spec: VELDO-0108
    title: Remote clients reach the same endpoint through an authenticated SSH command relay, not a second server
    feature_refs: [F2]
    depends_on: [VELDO-0107]
    order: 12108
    release: 1
    stage: 2
  - item: W86
    spec: VELDO-0109
    title: An unreachable authority stops mutation and admission, and never becomes a local one
    feature_refs: [F2]
    depends_on: [VELDO-0107]
    order: 11109
    release: 1
    stage: 1
  - item: W15
    spec: VELDO-0030
    title: Exclusive leadership and authority-generation fencing
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0029]
    order: 20030
    release: 2
  - item: W16
    spec: VELDO-0031
    title: Authority-backed claims and claim-generation fencing
    feature_refs: [F2]
    depends_on: [VELDO-0023, VELDO-0025, VELDO-0029, VELDO-0107]
    order: 11031
    release: 1
    stage: 1
  - item: W17
    spec: VELDO-0032
    title: Clock uncertainty in task reporting
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0031]
    order: 20032
    release: 2
  - item: W18
    spec: VELDO-0033
    title: Clock claim-refusal propagation through execution and landing
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0031]
    order: 20033
    release: 2
  - item: W19
    spec: VELDO-0034
    title: Clock uncertainty in the status display
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0031]
    order: 20034
    release: 2
  - item: W20
    spec: VELDO-0035
    title: Complete read-set validation and authoritative snapshots
    feature_refs: [F2]
    depends_on: [VELDO-0023, VELDO-0025]
    order: 11035
    release: 1
    stage: 1
  - item: W21
    spec: VELDO-0036
    title: Durable capacity and spend reservations
    feature_refs: [F2]
    depends_on: [VELDO-0023, VELDO-0025]
    order: 11036
    release: 1
    stage: 1
  - item: W22
    spec: VELDO-0037
    title: Atomic specification alias allocation and document publication
    feature_refs: [F2]
    depends_on: [VELDO-0023, VELDO-0035]
    order: 14037
    release: 1
    stage: 4
  - item: W23
    spec: VELDO-0038
    title: Effect-specific reconciliation and recovery commands
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0024, VELDO-0028, VELDO-0030, VELDO-0031, VELDO-0035, VELDO-0036]
    order: 20038
    release: 2
  - item: W24
    spec: VELDO-0039
    title: Durable dispatch acceptance and launch records
    feature_refs: [F2]
    depends_on: [VELDO-0028, VELDO-0031, VELDO-0036]
    order: 11039
    release: 1
    stage: 1
  - item: W25
    spec: VELDO-0040
    title: Provider-neutral process supervision and descendant containment
    feature_refs: [F2]
    depends_on: [VELDO-0039]
    order: 11040
    release: 1
    stage: 1
  - item: W26
    spec: VELDO-0041
    title: Independent heartbeat, bounded stopping, and safe capacity retirement
    feature_refs: [F2]
    depends_on: [VELDO-0036, VELDO-0039, VELDO-0040]
    order: 11041
    release: 1
    stage: 1
  - item: W27
    spec: VELDO-0042
    title: Isolated worker clones and pinned read-only shared object cache
    feature_refs: [F2]
    depends_on: [VELDO-0029, VELDO-0031, VELDO-0040]
    order: 11042
    release: 1
    stage: 1
  - item: W28
    spec: VELDO-0043
    title: Replaceable LangGraph execution adapter
    feature_refs: [F2]
    depends_on: [VELDO-0035]
    order: 14043
    release: 1
    stage: 4
  - item: W29
    spec: VELDO-0044
    title: Checkpoint namespace isolation and bounded contention
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0043]
    order: 20044
    release: 2
  - item: W30
    spec: VELDO-0045
    title: Pinned isolated runtime, dependency licenses, and distribution inventory
    feature_refs: [F2]
    depends_on: [VELDO-0043]
    order: 14045
    release: 1
    stage: 4
  - item: W31
    spec: VELDO-0046
    title: Durable wake-up, cursor replay, and notification delivery
    feature_refs: [F2]
    depends_on: [VELDO-0023, VELDO-0107]
    order: 11046
    release: 1
    stage: 1
  - item: W32
    spec: VELDO-0047
    title: Authority service installation, startup, stop, and absent-service behavior
    feature_refs: [F2]
    depends_on: [VELDO-0023, VELDO-0025, VELDO-0027, VELDO-0029, VELDO-0040, VELDO-0046, VELDO-0107]
    order: 11047
    release: 1
    stage: 1
  - item: W33
    spec: VELDO-0048
    title: Integrity verification, replica restoration, and host-replacement fencing
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0024, VELDO-0038, VELDO-0047]
    order: 20048
    release: 2
  - item: W34
    spec: VELDO-0049
    title: Dispatch and tracker bridge consume authoritative state transitions
    feature_refs: [F3]
    depends_on: [VELDO-0031, VELDO-0035, VELDO-0039]
    order: 11049
    release: 1
    stage: 1
  - item: W35
    spec: VELDO-0050
    title: Executor persists proof and performs complete contextual validation
    feature_refs: [F3]
    depends_on: [VELDO-0035, VELDO-0049]
    order: 11050
    release: 1
    stage: 1
  - item: W36
    spec: VELDO-0051
    title: Canonical event vocabulary and journal-derived publication
    feature_refs: [F3]
    depends_on: [VELDO-0023, VELDO-0035, VELDO-0050]
    order: 11051
    release: 1
    stage: 1
  - item: W37
    spec: VELDO-0052
    title: Shared eligibility in work, frontier, plan, direct executor, and review
    feature_refs: [F3]
    depends_on: [VELDO-0021, VELDO-0025, VELDO-0031, VELDO-0035, VELDO-0036]
    order: 11052
    release: 1
    stage: 1
  - item: W38
    spec: VELDO-0053
    title: Architecture failure handling at every eligibility entry
    feature_refs: [F3]
    depends_on: [VELDO-0016, VELDO-0052]
    order: 11053
    release: 1
    stage: 1
  - item: W39
    spec: VELDO-0054
    title: Decision-record dependency evaluation for the floor slice
    feature_refs: [F3]
    depends_on: [VELDO-0020, VELDO-0035, VELDO-0052]
    order: 11054
    release: 1
    stage: 1
  - item: W40
    spec: VELDO-0055
    title: Release regression receipt consumption
    feature_refs: [F3]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0052]
    order: 30055
    release: 3
  - item: W41
    spec: VELDO-0056
    title: Disposable landing candidate construction and failure isolation
    feature_refs: [F3]
    depends_on: [VELDO-0042, VELDO-0050, VELDO-0052]
    order: 11056
    release: 1
    stage: 1
  - item: W42
    spec: VELDO-0057
    title: Exact-tip publication, lost acknowledgement recovery, and completion receipt
    feature_refs: [F3]
    depends_on: [VELDO-0028, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0056, VELDO-0058]
    order: 11057
    release: 1
    stage: 1
  - item: W43
    spec: VELDO-0058
    title: Gate-output isolation and exact tested-tree evidence
    feature_refs: [F3]
    depends_on: [VELDO-0050, VELDO-0056]
    order: 11058
    release: 1
    stage: 1
  - item: W44
    spec: VELDO-0059
    title: Installed end-to-end floor slice with fake model and real enforcement
    feature_refs: [F3]
    depends_on: [VELDO-0037, VELDO-0043, VELDO-0045, VELDO-0047, VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0057, VELDO-0058, VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0069, VELDO-0073, VELDO-0075, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0085, VELDO-0088, VELDO-0089, VELDO-0090, VELDO-0091, VELDO-0092, VELDO-0108, VELDO-0124, VELDO-0125, VELDO-0126, VELDO-0127, VELDO-0128, VELDO-0129, VELDO-0130, VELDO-0131, VELDO-0132]
    order: 16059
    release: 1
    stage: 6
  - item: W45
    spec: VELDO-0060
    title: Claude Code production adapter qualification
    feature_refs: [F4]
    depends_on: [VELDO-0028, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0062]
    order: 11060
    release: 1
    stage: 1
  - item: W46
    spec: VELDO-0061
    title: Codex production adapter qualification
    feature_refs: [F4]
    depends_on: [VELDO-0028, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0062]
    order: 11061
    release: 1
    stage: 1
  - item: W47
    spec: VELDO-0062
    title: Provider credential separation and live usage accounting
    feature_refs: [F4]
    depends_on: [VELDO-0028, VELDO-0036]
    order: 11062
    release: 1
    stage: 1
  - item: W48
    spec: VELDO-0063
    title: Production governor and lifecycle failure qualification
    feature_refs: [F4]
    depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0060, VELDO-0061, VELDO-0062]
    order: 20063
    release: 2
  - item: W49
    spec: VELDO-0064
    title: Assignment inbox and durable projections on enrolled input surfaces
    feature_refs: [F5]
    depends_on: [VELDO-0025, VELDO-0035, VELDO-0046]
    order: 13064
    release: 1
    stage: 3
  - item: W50
    spec: VELDO-0065
    title: Versioned presentation receipts for every enrolled channel
    feature_refs: [F5]
    depends_on: [VELDO-0064]
    order: 13065
    release: 1
    stage: 3
  - item: W51
    spec: VELDO-0066
    title: Canonical channel attribution including platform-derived chat message, sender, and time
    feature_refs: [F5]
    depends_on: [VELDO-0020, VELDO-0065]
    order: 13066
    release: 1
    stage: 3
  - item: W52
    spec: VELDO-0067
    title: Per-channel restricted edge signing and enrollment
    feature_refs: [F5]
    depends_on: [VELDO-0025, VELDO-0027, VELDO-0066]
    order: 13067
    release: 1
    stage: 3
  - item: W53
    spec: VELDO-0068
    title: Atomic cross-channel settlement and principal-based quorum enforcement
    feature_refs: [F5]
    depends_on: [VELDO-0035, VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067]
    order: 13068
    release: 1
    stage: 3
  - item: W54
    spec: VELDO-0069
    title: Governing decision binding, supersession, and eligibility updates
    feature_refs: [F5]
    depends_on: [VELDO-0054, VELDO-0068]
    order: 13069
    release: 1
    stage: 3
  - item: W55
    spec: VELDO-0070
    title: Independent decision review bound to full framing and distinct principals
    feature_refs: [F5]
    depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0069]
    order: 30070
    release: 3
  - item: W56
    spec: VELDO-0071
    title: Governing assumption observations and tripwire review flow
    feature_refs: [F5]
    depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0069, VELDO-0070]
    order: 30071
    release: 3
  - item: W57
    spec: VELDO-0072
    title: PLAN-0016 tracker projection and canonical-history repair
    feature_refs: [F5]
    depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0065, VELDO-0066, VELDO-0068]
    order: 40072
    release: 4
  - item: W58
    spec: VELDO-0073
    title: Per-channel live ingress activation and real sandbox qualification
    feature_refs: [F5]
    depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0126]
    order: 13073
    release: 1
    stage: 3
  - item: W59
    spec: VELDO-0074
    title: Interrupted and concurrent decisions across enrolled channels
    feature_refs: [F5]
    depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0068, VELDO-0069, VELDO-0073]
    order: 20074
    release: 2
  - item: W60
    spec: VELDO-0075
    title: Andon delivery and authorized resumption through enrolled channels
    feature_refs: [F5]
    depends_on: [VELDO-0046, VELDO-0069, VELDO-0073]
    order: 13075
    release: 1
    stage: 3
  - item: W61
    spec: VELDO-0076
    title: Project ownership, charter, lifecycle, and transfers
    feature_refs: [F6]
    depends_on: [VELDO-0025, VELDO-0035, VELDO-0036, VELDO-0068, VELDO-0073]
    order: 14076
    release: 1
    stage: 4
  - item: W62
    spec: VELDO-0077
    title: Objective acceptance and signed outcome assessment
    feature_refs: [F6]
    depends_on: [VELDO-0076, VELDO-0069, VELDO-0126]
    order: 14077
    release: 1
    stage: 4
  - item: W63
    spec: VELDO-0078
    title: Backlog lifecycle and priority-controlled execution
    feature_refs: [F6]
    depends_on: [VELDO-0052, VELDO-0076, VELDO-0077]
    order: 14078
    release: 1
    stage: 4
  - item: W64
    spec: VELDO-0079
    title: Grooming and admission requests through enrolled decision surfaces
    feature_refs: [F6]
    depends_on: [VELDO-0065, VELDO-0068, VELDO-0069, VELDO-0073, VELDO-0078]
    order: 14079
    release: 1
    stage: 4
  - item: W65
    spec: VELDO-0080
    title: Section 2 work-class dispatch and trusted defect reproduction
    feature_refs: [F6]
    depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0079]
    order: 30080
    release: 3
  - item: W66
    spec: VELDO-0081
    title: Quarantine inspection, taint propagation, and bounded execution
    feature_refs: [F6]
    depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0078]
    order: 30081
    release: 3
  - item: W67
    spec: VELDO-0082
    title: Standing maintenance and compliance occurrence admission
    feature_refs: [F6]
    depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0079, VELDO-0081]
    order: 30082
    release: 3
  - item: W68
    spec: VELDO-0083
    title: Bounded security emergency and incident containment admission
    feature_refs: [F6]
    depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0079, VELDO-0081]
    order: 30083
    release: 3
  - item: W69
    spec: VELDO-0084
    title: Readmission, scope enforcement, and admission-debt reporting
    feature_refs: [F6]
    depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0079]
    order: 30084
    release: 3
  - item: W70
    spec: VELDO-0085
    title: Decomposition and concurrent elaboration publication
    feature_refs: [F6]
    depends_on: [VELDO-0037, VELDO-0078, VELDO-0079]
    order: 14085
    release: 1
    stage: 4
  - item: W71
    spec: VELDO-0086
    title: Release-execution ownership and contribution binding
    feature_refs: [F6]
    depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0076, VELDO-0077]
    order: 30086
    release: 3
  - item: W72
    spec: VELDO-0087
    title: Project dependency invalidation and outcome-to-evidence traceability
    feature_refs: [F6]
    depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0084, VELDO-0085, VELDO-0086]
    order: 30087
    release: 3
  - item: W73
    spec: VELDO-0088
    title: Project-manager execution graphs
    feature_refs: [F7]
    depends_on: [VELDO-0035, VELDO-0043, VELDO-0045, VELDO-0060, VELDO-0061, VELDO-0076, VELDO-0078, VELDO-0079, VELDO-0132]
    order: 14088
    release: 1
    stage: 4
  - item: W74
    spec: VELDO-0089
    title: Versioned team configuration
    feature_refs: [F7]
    depends_on: [VELDO-0025, VELDO-0036, VELDO-0049, VELDO-0076]
    order: 14089
    release: 1
    stage: 4
  - item: W75
    spec: VELDO-0090
    title: Capability-bound specialist selection
    feature_refs: [F7]
    depends_on: [VELDO-0036, VELDO-0060, VELDO-0061, VELDO-0089, VELDO-0108, VELDO-0125, VELDO-0127]
    order: 14090
    release: 1
    stage: 4
  - item: W76
    spec: VELDO-0091
    title: Budgeted requirements elaboration
    feature_refs: [F7]
    depends_on: [VELDO-0037, VELDO-0062, VELDO-0079, VELDO-0085, VELDO-0088, VELDO-0090]
    order: 14091
    release: 1
    stage: 4
  - item: W77
    spec: VELDO-0092
    title: Typed proposals and complete authorization validation
    feature_refs: [F7]
    depends_on: [VELDO-0035, VELDO-0052, VELDO-0054, VELDO-0069, VELDO-0078, VELDO-0085, VELDO-0089, VELDO-0091]
    order: 14092
    release: 1
    stage: 4
  - item: W78
    spec: VELDO-0093
    title: Per-project cycle serialization and replaceable checkpoint recovery
    feature_refs: [F7]
    depends_on: [VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0085, VELDO-0088, VELDO-0089, VELDO-0090, VELDO-0091, VELDO-0092]
    order: 20093
    release: 2
  - item: W79
    spec: VELDO-0094
    title: Every-pack runtime installation and floor-slice qualification
    feature_refs: [F8]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087, VELDO-0088, VELDO-0089, VELDO-0090, VELDO-0091, VELDO-0092, VELDO-0093]
    order: 40094
    release: 4
  - item: W80
    spec: VELDO-0095
    title: Historical migration and atomic reader-writer cutover
    feature_refs: [F8]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087, VELDO-0088, VELDO-0089, VELDO-0090, VELDO-0091, VELDO-0092, VELDO-0093, VELDO-0094]
    order: 40095
    release: 4
  - item: W81
    spec: VELDO-0096
    title: Clone and enrolled-principal adoption qualification
    feature_refs: [F8]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087, VELDO-0088, VELDO-0089, VELDO-0090, VELDO-0091, VELDO-0092, VELDO-0093, VELDO-0094, VELDO-0095]
    order: 40096
    release: 4
  - item: W82
    spec: VELDO-0097
    title: Operational recovery under scope change, revocation, and lost effect acknowledgement
    feature_refs: [F8]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0085, VELDO-0088, VELDO-0089, VELDO-0090, VELDO-0091, VELDO-0092, VELDO-0093]
    order: 20097
    release: 2
  - item: W83
    spec: VELDO-0098
    title: Rollback compatibility and coordinated release qualification
    feature_refs: [F8]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087, VELDO-0088, VELDO-0089, VELDO-0090, VELDO-0091, VELDO-0092, VELDO-0093, VELDO-0094, VELDO-0095, VELDO-0096, VELDO-0097]
    order: 40098
    release: 4
  - item: W87
    spec: VELDO-0124
    title: Simple macOS worker lifecycle profile
    feature_refs: [F2]
    depends_on: [VELDO-0039, VELDO-0041, VELDO-0042, VELDO-0062]
    order: 12124
    release: 1
    stage: 2
  - item: W88
    spec: VELDO-0125
    title: Mac worker dispatch through the relay with host-capability routing
    feature_refs: [F2]
    depends_on: [VELDO-0039, VELDO-0047, VELDO-0108, VELDO-0124]
    order: 12125
    release: 1
    stage: 2
  - item: W89
    spec: VELDO-0126
    title: One Telegram and API message intake for proposed work
    feature_refs: [F5]
    depends_on: [VELDO-0025, VELDO-0035, VELDO-0047]
    order: 13126
    release: 1
    stage: 3
  - item: W90
    spec: VELDO-0127
    title: Versioned per-role MCP server and tool configuration
    feature_refs: [F7]
    depends_on: [VELDO-0025, VELDO-0035, VELDO-0089]
    order: 14127
    release: 1
    stage: 4
  - item: W91
    spec: VELDO-0128
    title: Telegram progress and completion from journal events
    feature_refs: [F5]
    depends_on: [VELDO-0046, VELDO-0051, VELDO-0073, VELDO-0075]
    order: 13128
    release: 1
    stage: 3
  - item: W92
    spec: VELDO-0129
    title: Real worker adapter wiring for LiveLoop and LiveReviewer
    feature_refs: [F4]
    depends_on: [VELDO-0049, VELDO-0050, VELDO-0060, VELDO-0061]
    order: 11129
    release: 1
    stage: 1
  - item: W93
    spec: VELDO-0130
    title: Authenticated factory state, message and decision API
    feature_refs: [F9]
    depends_on: [VELDO-0025, VELDO-0035, VELDO-0047, VELDO-0064, VELDO-0065, VELDO-0068, VELDO-0069, VELDO-0126]
    order: 15130
    release: 1
    stage: 5
  - item: W94
    spec: VELDO-0131
    title: Veldo factory UI on phone and desktop
    feature_refs: [F9]
    depends_on: [VELDO-0051, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0089, VELDO-0127, VELDO-0128, VELDO-0130, VELDO-0132]
    order: 15131
    release: 1
    stage: 5
  - item: W95
    spec: VELDO-0132
    title: Versioned workflow definitions consumed by LangGraph
    feature_refs: [F7]
    depends_on: [VELDO-0035, VELDO-0043]
    order: 14132
    release: 1
    stage: 4

regression:
  journeys:
    - id: RJ1
      title: Release 1 full installed Telegram or API objective through LangGraph PM, Linux and Mac workers, proof, review, exact landing and owner completion
      activation: {when: after:VELDO-0059}
      owner_spec: VELDO-0059
      release: 1
      profiles: [per_spec, release]
      suite: PLAN-0019 RJ1 (planned; implementation must register executable checks)
    - id: RJ2
      title: Release 1 red gate, forged or stale answer, missing approval and self-review refuse and preserve trunk
      activation: {when: after:VELDO-0059}
      owner_spec: VELDO-0059
      release: 1
      profiles: [per_spec, release]
      suite: PLAN-0019 RJ2 (planned; implementation must register executable checks)
    - id: RJ3
      title: Release 1 current dependency, authority and pre-call cap checks hold at selection, review and publication
      activation: {when: after:VELDO-0059}
      owner_spec: VELDO-0059
      release: 1
      profiles: [per_spec, release]
      suite: PLAN-0019 RJ3 (planned; implementation must register executable checks)
    - id: RJ4
      title: Release 2 lost landing acknowledgement recovery without second publication
      activation: {when: after:VELDO-0097}
      owner_spec: VELDO-0097
      release: 2
      profiles: [per_spec, release]
      suite: PLAN-0019 RJ4 (planned; implementation must register executable checks)
    - id: RJ5
      title: Release 2 concurrent inputs, repeated graphs and exhaustive read-set qualification
      activation: {when: after:VELDO-0093}
      owner_spec: VELDO-0093
      release: 2
      profiles: [per_spec, release]
      suite: PLAN-0019 RJ5 (planned; implementation must register executable checks)
    - id: RJ6
      title: Release 2 deterministic replacement adapter equivalence matrix
      activation: {when: after:VELDO-0093}
      owner_spec: VELDO-0093
      release: 2
      profiles: [per_spec, release]
      suite: PLAN-0019 RJ6 (planned; implementation must register executable checks)
    - id: RJ7
      title: Release 2 checkpoint loss, disagreement and restoration preserve domain history
      activation: {when: after:VELDO-0093}
      owner_spec: VELDO-0093
      release: 2
      profiles: [per_spec, release]
      suite: PLAN-0019 RJ7 (planned; implementation must register executable checks)
    - id: RJ8
      title: Release 4 every composed pack installs the declared inventory and runs the journey
      activation: {when: after:VELDO-0094}
      owner_spec: VELDO-0094
      release: 4
      profiles: [per_spec, release]
      suite: PLAN-0019 RJ8 (planned; implementation must register executable checks)
    - id: RJ9
      title: Release 4 adopter, migration and rollback compatibility on additional qualified hosts
      activation: {when: after:VELDO-0098}
      owner_spec: VELDO-0098
      release: 4
      profiles: [per_spec, release]
      suite: PLAN-0019 RJ9 (planned; implementation must register executable checks)
    - id: RJ10
      title: Release 2 scope change, revocation and lost effect acknowledgement combined recovery
      activation: {when: after:VELDO-0097}
      owner_spec: VELDO-0097
      release: 2
      profiles: [per_spec, release]
      suite: PLAN-0019 RJ10 (planned; implementation must register executable checks)
    - id: RJ11
      title: Release 1 Mac relay commands reach Linux authority and iOS work never falls back to Linux
      activation: {when: after:VELDO-0125}
      owner_spec: VELDO-0125
      release: 1
      profiles: [per_spec, release]
      suite: PLAN-0019 Mac routing (planned; implementation must register executable checks)
    - id: RJ12
      title: Release 1 authenticated UI message and decision flow on phone and desktop with workflow edits that never execute
      activation: {when: after:VELDO-0131}
      owner_spec: VELDO-0131
      release: 1
      profiles: [per_spec, release]
      suite: PLAN-0019 UI and API (planned; implementation must register executable checks)

release:
  milestone: Dark Factory roadmap - Release 1 running journey, then recovery, governance and scale
  mode: continuous
  require_all_work_shipped: false
  require_full_regression: false
  rollback: >
    Release 1 stops new work on uncertainty and preserves evidence; no automatic retry,
    restoration or rollback is promised. Release 2 qualifies recovery; Release 4 qualifies
    migration and rollback. Each release requires its assigned work and applicable journeys.
  observation:
    duration: Release 1 requires the actual installed full journey; later release matrices do not gate the MVP.

open_decisions: []
---

## Intent

Revision 3 records the owner's 2026-09-22 scope decisions. Release 1 is a functioning dark factory,
including Claude Code, Codex, LangGraph, this Linux box, the Mac, Telegram, the API and the UI.
The authority remains in Veldo on Linux. Models reason and propose; authenticated deterministic
services authorize and commit. Independent review, authentic answers, pre-call spend bounds and
publication of exactly the tested tree are part of the function.

## Releases and order

Release 1 is delivered in six stages. Within each stage `depends_on` is the actual functional DAG;
`order` is only a tie-breaker. Packages A-H remain feature labels, not completion barriers. A later
stage may integrate an earlier service without making that service depend on the final journey.

1. **Delivery.** Claims and explicit dispatch, a real authenticated IPC request applied to the real
   configured SQLite store, local service exclusion, snapshots/materialization, reservations,
   Linux worker groups, isolated clones, live Claude Code and Codex adapters, real build/review
   wiring, proof, shared eligibility, isolated gate observations, exact-tip publication and journal
   completion. Provision minimal accepted owner/project/admission records for integration checks.
2. **Mac and relay.** Qualify the Mac's simple worker lifecycle and connect its workers through
   built VELDO-0108 to the Linux authority. Route macOS/iOS work only to a qualified Mac.
3. **Telegram decisions.** Common message intake, actual Telegram enrollment and send/receive,
   exact versioned presentations, canonical owner attribution, atomic settlements and governing
   decision bindings, clean decision-stop resumption, ordinary progress/stop/completion reports.
4. **Projects and the LangGraph project manager.** Project/owner/charter and objective acceptance,
   prioritized backlog and published specification decomposition, bounded PM elaboration, versioned
   teams and exact agent/tool/MCP configuration, specialist matching and typed authorized proposals.
   One cycle runs per project, with one bounded follow-up if relevant input arrives during it.
   LangGraph runs a Veldo-owned versioned workflow through a replaceable plain-data interface;
   Release 1 uses no persistent checkpointer. Install all runtime assets this journey needs.
5. **UI and API.** Authenticated reads, message submission and decision answers; the UI message box
   uses the same intake API. Phone and desktop screens show and control the journey. The workflow
   editor edits versioned data and never executes work. Telegram and UI answers bind the same
   current request and settle at most once, including a simple conflicting-answer check.
6. **Full-journey test.** VELDO-0059 begins with an actual Telegram objective and also exercises the
   authenticated API/UI entry. LangGraph asks the owner, grooms specifications and priorities,
   obtains admission, assigns specialists from a versioned team on Linux and Mac, builds isolated
   clones, keeps proof, runs the gate outside the candidate, obtains fresh independent review,
   lands the exact tested tree, records completion and reports it on Telegram and in the UI.
   Real engines and real authenticated owner-channel paths require their own qualification;
   deterministic model fixtures supplement, never replace, live journey evidence.

Release 2 delivers robustness and recovery: off-host acknowledgement, authority generations and
fencing, clock follow-ups, recovery commands, checkpoint isolation and restoration, replay and lost
acknowledgements, governor failure matrices, interrupted decisions and operational recovery.
Unknown effects remain stopped in Release 1 with original dispatch identity and charge exposure;
a process exit is not evidence that a remote operation did not happen. Ordinary unavailable-service
checks and actual IPC-to-store integration are required now without claiming the broader follow-up
qualification matrices have been proven.

Release 3 adds governance depth: full regression receipt consumers, adversarial decision review
and tripwires, advanced work classes and quarantine, standing/emergency admission, readmission debt,
release-execution ownership and project-wide dependency invalidation. Release 1 consumes exact
normal decision settlements and existing engineering-review policy. Unsupported governing obligations
block admission; they are never treated as satisfied because their richer consumer is deferred.

Release 4 adds scale: cloud and other host kinds, additional explicitly chosen channels, full asset
inventory and every-pack installation, adopters, migration and rollback. W57/VELDO-0072 is retained
as a Release 4 historical disposition only: its Jira tracker intake is dropped by Telegram 28857
and 28859, not scheduled to be built in that release. No later release silently re-enables Jira intake.

The YAML `release` and `stage` annotations and the table below assign every existing and new work item.
The roadmap's continuous-release flags prevent all four releases becoming a single MVP barrier. They do
not waive a release's own work or regression: Release 1 requires every assigned functional item
and RJ1-RJ3/RJ11-RJ12; Release 2 requires its work and RJ4-RJ7/RJ10; Release 3 requires its governance evidence;
Release 4 requires its active work and RJ8-RJ9. The retained dropped W57 is not an activation gate.
These are writing-only allocations; no specification status or existing evidence is re-certified.

## Complete work allocation

| Work | Specification | Release | Stage or disposition |
|---|---|---|---|
| W1 | VELDO-0016 | 1 | 1 |
| W2 | VELDO-0017 | 1 | 1 |
| W3 | VELDO-0018 | 1 | 1 |
| W4 | VELDO-0019 | 1 | 1 |
| W5 | VELDO-0020 | 1 | 1 |
| W6 | VELDO-0021 | 1 | 1 |
| W7 | VELDO-0022 | 1 | 1 |
| W8 | VELDO-0023 | 1 | 1 |
| W9 | VELDO-0024 | 2 | - |
| W10 | VELDO-0025 | 1 | 1 |
| W11 | VELDO-0026 | 1 | 1 |
| W12 | VELDO-0027 | 1 | 1 |
| W13 | VELDO-0028 | 1 | 1 |
| W14 | VELDO-0029 | 1 | 1 |
| W84 | VELDO-0107 | 1 | 1 |
| W85 | VELDO-0108 | 1 | 2 |
| W86 | VELDO-0109 | 1 | 1 |
| W15 | VELDO-0030 | 2 | - |
| W16 | VELDO-0031 | 1 | 1 |
| W17 | VELDO-0032 | 2 | - |
| W18 | VELDO-0033 | 2 | - |
| W19 | VELDO-0034 | 2 | - |
| W20 | VELDO-0035 | 1 | 1 |
| W21 | VELDO-0036 | 1 | 1 |
| W22 | VELDO-0037 | 1 | 4 |
| W23 | VELDO-0038 | 2 | - |
| W24 | VELDO-0039 | 1 | 1 |
| W25 | VELDO-0040 | 1 | 1 |
| W26 | VELDO-0041 | 1 | 1 |
| W27 | VELDO-0042 | 1 | 1 |
| W28 | VELDO-0043 | 1 | 4 |
| W29 | VELDO-0044 | 2 | - |
| W30 | VELDO-0045 | 1 | 4 |
| W31 | VELDO-0046 | 1 | 1 |
| W32 | VELDO-0047 | 1 | 1 |
| W33 | VELDO-0048 | 2 | - |
| W34 | VELDO-0049 | 1 | 1 |
| W35 | VELDO-0050 | 1 | 1 |
| W36 | VELDO-0051 | 1 | 1 |
| W37 | VELDO-0052 | 1 | 1 |
| W38 | VELDO-0053 | 1 | 1 |
| W39 | VELDO-0054 | 1 | 1 |
| W40 | VELDO-0055 | 3 | - |
| W41 | VELDO-0056 | 1 | 1 |
| W42 | VELDO-0057 | 1 | 1 |
| W43 | VELDO-0058 | 1 | 1 |
| W44 | VELDO-0059 | 1 | 6 |
| W45 | VELDO-0060 | 1 | 1 |
| W46 | VELDO-0061 | 1 | 1 |
| W47 | VELDO-0062 | 1 | 1 |
| W48 | VELDO-0063 | 2 | - |
| W49 | VELDO-0064 | 1 | 3 |
| W50 | VELDO-0065 | 1 | 3 |
| W51 | VELDO-0066 | 1 | 3 |
| W52 | VELDO-0067 | 1 | 3 |
| W53 | VELDO-0068 | 1 | 3 |
| W54 | VELDO-0069 | 1 | 3 |
| W55 | VELDO-0070 | 3 | - |
| W56 | VELDO-0071 | 3 | - |
| W57 | VELDO-0072 | 4 | Dropped Jira intake; retained history |
| W58 | VELDO-0073 | 1 | 3 |
| W59 | VELDO-0074 | 2 | - |
| W60 | VELDO-0075 | 1 | 3 |
| W61 | VELDO-0076 | 1 | 4 |
| W62 | VELDO-0077 | 1 | 4 |
| W63 | VELDO-0078 | 1 | 4 |
| W64 | VELDO-0079 | 1 | 4 |
| W65 | VELDO-0080 | 3 | - |
| W66 | VELDO-0081 | 3 | - |
| W67 | VELDO-0082 | 3 | - |
| W68 | VELDO-0083 | 3 | - |
| W69 | VELDO-0084 | 3 | - |
| W70 | VELDO-0085 | 1 | 4 |
| W71 | VELDO-0086 | 3 | - |
| W72 | VELDO-0087 | 3 | - |
| W73 | VELDO-0088 | 1 | 4 |
| W74 | VELDO-0089 | 1 | 4 |
| W75 | VELDO-0090 | 1 | 4 |
| W76 | VELDO-0091 | 1 | 4 |
| W77 | VELDO-0092 | 1 | 4 |
| W78 | VELDO-0093 | 2 | - |
| W79 | VELDO-0094 | 4 | - |
| W80 | VELDO-0095 | 4 | - |
| W81 | VELDO-0096 | 4 | - |
| W82 | VELDO-0097 | 2 | - |
| W83 | VELDO-0098 | 4 | - |
| W87 | VELDO-0124 | 1 | 2 |
| W88 | VELDO-0125 | 1 | 2 |
| W89 | VELDO-0126 | 1 | 3 |
| W90 | VELDO-0127 | 1 | 4 |
| W91 | VELDO-0128 | 1 | 3 |
| W92 | VELDO-0129 | 1 | 1 |
| W93 | VELDO-0130 | 1 | 5 |
| W94 | VELDO-0131 | 1 | 5 |
| W95 | VELDO-0132 | 1 | 4 |

## Related baseline and follow-up disposition

These standalone or PLAN-0020 items retain their existing binding and status; they are not silently
moved into PLAN-0019's work graph. VELDO-0099 is existing installation evidence usable by Release 1;
VELDO-0100's confinement qualification belongs to Release 2. VELDO-0101 through VELDO-0106 remain
PLAN-0020 review machinery, existing evidence rather than new MVP runtime gates. VELDO-0110 is an
existing reader foundation. VELDO-0111 through VELDO-0117, VELDO-0121 and VELDO-0122 are Release 2
qualification follow-ups; the actual single-domain store connection from 0115 is required in 0047
now. VELDO-0118 through VELDO-0120 and VELDO-0123 are Release 2 parser/gate qualification, including
already recorded evidence. A release assignment does not undo code or change a status field.

## Revision history and dependency basis

2026-09-22: revision 3 replaces package completion barriers with release-scoped functional edges,
amends C3/C5/C7/C10/C11/C12/NG3 and adds C14-C17 under the owner rulings quoted there. It preserves
C13's commit-pinned, named, read-only attachments. The analyses `ask-20260922-213601.md` sections 1-4
and `ask-20260922-212450.md` in the owner's research/codex-reviews directory supply the trim and
consumption basis; the later Mac, UI/API and no-Jira decisions override their narrower suggestions.
VELDO-0035, 0054 and 0069 retain consumed normal functions; 0053 retains required architecture entry
checks. 0089 consumes retained engineering review, not deferred 0070 adversarial decision review.
0047 incorporates local exclusion from 0030 and normal real-store wiring from 0115; 0088 incorporates
ordinary cycle serialization from 0093. Their broader matrices keep their later release allocation.
Nine new draft specifications, VELDO-0124 through VELDO-0132, fill the host, routing, intake,
capability, reporting, live wiring, API, UI and workflow-definition concerns in this same graph. The final writing audit lives in proof/plan-0019-rev3/README.md.
