---
schema: veldo.plan/v1
id: PLAN-0019
title: Dark Factory project coordination inside Veldo
kind: mvp
status: ready
revision: 4
owner: dmitry
approved_by: dmitry
approved_at: 2026-09-25
risk: critical

outcomes:
  - id: O1
    becomes_true: >
      Project owners can trace an accepted objective through deliberately admitted work and give a
      version-bound decision on the enrolled input surface where they are working.
    measure: >
      Release 1: every admitted item resolves to its owner, accepted request and priority; answers
      from enrolled channels produce one attributable settlement with the exact presentation
      receipt. Release 2 qualifies the exhaustive concurrent-answer and recovery matrix.
  - id: O2
    becomes_true: >
      Operators can restart or replace the authority without repeating an uncertain effect or losing
      acknowledged history.
    measure: >
      Release 2: real-process boundary crashes, replica restoration, and the combined scope-change and lost-
      effect-acknowledgement journey produce verified recovery or a named authority stop; no
      acknowledged command lacks its durable off-host export.
  - id: O3
    becomes_true: >
      Builders and reviewers can rely on completion meaning verified, independently reviewed,
      authorized publication of the exact candidate and accepted outcomes.
    measure: >
      Release 1: the installed floor slice lands successfully; red gates, rejected approvals, stale
      dependencies, missing regression receipts, and build-only attempts cannot establish
      completion.
  - id: O4
    becomes_true: >
      Project owners can delegate bounded coordination and engineering to qualified workers without
      granting models admission authority or unlimited cost and process lifetime.
    measure: >
      Release 1: real Claude Code and Codex workers on Linux and Mac pass normal containment,
      stopping, credential custody, subscription usage-cap accounting and current-authorization
      checks; a worker's tools may read their own engine login (Telegram 29163). Release 2:
      separation of the engine login from worker tools for both engines, recovery, revocation and
      exhaustive containment qualification, including
      repeated graphs and deleted checkpoints that cannot repeat a committed effect or change
      authoritative decisions. Release 4: qualification extends to every additional supported
      engine configuration and host profile.
  - id: O5
    becomes_true: >
      Adopters can install the same governed factory from every composed pack and recover with a
      compatible previous release.
    measure: >
      Release 4: every installed pack runs the first slice and migration, clone replacement, host-loss,
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
      Amended 2026-09-22 by owner Telegram 28857: "we definitly will need some form of UI, otherwise we'll be flying blind"
      Ruling applied: the prohibition on a new management console
      is removed. Veldo's own phone and desktop UI is in Release 1. Unverified Jira board
      changes, modifications to published prose and client-engagement material remain excluded.

constraints:
  - id: C1
    text: >
      The controlling design is docs/design/PLAN-0019-dark-factory-design.md, R01 through R76.
      Amended 2026-09-25 by owner Telegram 29162: "all 6 are yes", approving
      docs/design/PLAN-0019-operating-model-design.md at 12879d3, and 29163: "yes, Codex and Claude
      can read creds", answering its section 15.
      Ruling applied: the operating-model design governs the areas it covers (channels and
      referenced material, the MCP catalog and OS keystore, the project manager and factory loop,
      new repositories and Git identities, per-work capability handoff, the live execution record
      and re-landing, and the account pool); where it and the controlling design disagree on those
      areas, the operating-model design wins. Each person runs their own factory. Separating the
      engine login from worker tools is Release 2 for both engines. The
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
      owner Telegram 28848: "Claude code and langgraph can't be out. All of the recovery and robustness is definitly for later. Actually functionality for actual running dark factory can't be cut out. All sorts of durability, scalibility, all sorts of different machines, etc etc are definitly for later"
      Ruling applied: Release 1 accepts local committed authority results; off-host
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
      Amended 2026-09-22 by owner Telegram 28848: "Claude code and langgraph can't be out. All of the recovery and robustness is definitly for later. Actually functionality for actual running dark factory can't be cut out. All sorts of durability, scalibility, all sorts of different machines, etc etc are definitly for later"
      Ruling applied: install and qualify only the assets needed by the
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
      Amended 2026-09-22 by owner Telegram 28848: "Claude code and langgraph can't be out. All of the recovery and robustness is definitly for later. Actually functionality for actual running dark factory can't be cut out. All sorts of durability, scalibility, all sorts of different machines, etc etc are definitly for later"
      Ruling applied: VELDO-0032, VELDO-0033 and VELDO-0034 clock
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
      Amended 2026-09-22 by owner Telegram 28852: "Actually we need multi machine suport, since we need to run on Mac too, ios app can't be built on pc"
      Ruling applied: Release 1 qualifies this Linux box and a Mac
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
      Owner Telegram 28859, 2026-09-22: "No such thing as read only. You will have agents and mcps, so whatever is configured that is what's available to an agent. Do not reduce what's currently possible!"
      Ruling applied: each role's versioned capability configuration defines
      exactly the MCP servers and tools handed to its worker. The factory must not silently remove,
      replace or add capabilities available in that configuration. Unsupported handoff refuses
      visibly; no factory-specific Jira channel is needed. Existing scope, credential custody and
      C13 repository boundaries still apply to authorized use.
  - id: C16
    text: >
      Owner decision 2026-09-22 after stack comparison (UI requirement in Telegram 28857): Veldo
      uses React, TypeScript, Vite, shadcn/ui including its AI chat parts, TanStack Table, React
      Flow, Monaco and Chart.js with react-chartjs-2 (both MIT); shadcn charts and Recharts
      are prohibited. No Chinese-origin dependency anywhere and no library with free and paid
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
    title: Capacity and subscription usage reservations
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
    title: Exact-tip publication and confirmed completion receipt
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
    title: Installed full factory journey with real workers and enforcement
    feature_refs: [F3]
    depends_on: [VELDO-0037, VELDO-0043, VELDO-0045, VELDO-0047, VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0057, VELDO-0058, VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0069, VELDO-0073, VELDO-0075, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0085, VELDO-0088, VELDO-0089, VELDO-0090, VELDO-0091, VELDO-0108, VELDO-0124, VELDO-0125, VELDO-0126, VELDO-0127, VELDO-0128, VELDO-0129, VELDO-0130, VELDO-0131, VELDO-0132, VELDO-0140, VELDO-0141, VELDO-0142, VELDO-0143, VELDO-0144, VELDO-0145, VELDO-0146, VELDO-0147, VELDO-0148, VELDO-0149, VELDO-0150, VELDO-0151, VELDO-0152, VELDO-0153, VELDO-0154, VELDO-0155, VELDO-0156, VELDO-0157, VELDO-0158, VELDO-0159, VELDO-0160, VELDO-0161, VELDO-0162, VELDO-0163]
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
    title: Provider subscription logins and live usage accounting
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
    depends_on: [VELDO-0065, VELDO-0068, VELDO-0069, VELDO-0073, VELDO-0078, VELDO-0150]
    order: 14079
    release: 1
    stage: 4
  - item: W65
    spec: VELDO-0080
    title: Ordinary defect dispatch through normal admission
    feature_refs: [F6]
    depends_on: [VELDO-0079, VELDO-0126]
    order: 20080
    release: 2
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
    depends_on: [VELDO-0035, VELDO-0043, VELDO-0045, VELDO-0060, VELDO-0061, VELDO-0076, VELDO-0078, VELDO-0079, VELDO-0089, VELDO-0132, VELDO-0151, VELDO-0154]
    order: 15088
    release: 1
    stage: 5
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
    depends_on: [VELDO-0036, VELDO-0060, VELDO-0061, VELDO-0089, VELDO-0108, VELDO-0125, VELDO-0127, VELDO-0147, VELDO-0151]
    order: 15090
    release: 1
    stage: 5
  - item: W76
    spec: VELDO-0091
    title: Budgeted requirements elaboration
    feature_refs: [F7]
    depends_on: [VELDO-0037, VELDO-0062, VELDO-0079, VELDO-0085, VELDO-0088, VELDO-0090]
    order: 15091
    release: 1
    stage: 5
  - item: W77
    spec: VELDO-0092
    title: Typed proposals and complete authorization validation
    feature_refs: [F7]
    depends_on: [VELDO-0035, VELDO-0052, VELDO-0054, VELDO-0069, VELDO-0078, VELDO-0085, VELDO-0089, VELDO-0091]
    order: 20092
    release: 2
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
    depends_on: [VELDO-0025, VELDO-0035, VELDO-0089, VELDO-0141, VELDO-0144, VELDO-0155, VELDO-0156, VELDO-0158]
    order: 15127
    release: 1
    stage: 5
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
    depends_on: [VELDO-0039, VELDO-0049, VELDO-0050, VELDO-0060, VELDO-0061, VELDO-0155, VELDO-0156]
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
    depends_on: [VELDO-0051, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0089, VELDO-0127, VELDO-0128, VELDO-0130, VELDO-0132, VELDO-0141, VELDO-0142, VELDO-0143, VELDO-0144, VELDO-0145, VELDO-0159, VELDO-0160, VELDO-0162, VELDO-0163]
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
  - item: W96
    spec: VELDO-0133
    title: Ask what becomes of work whose person assignment is declined, canceled or expired
    feature_refs: [F5]
    depends_on: [VELDO-0064, VELDO-0126]
    order: 13133
    release: 1
    stage: 3
  - item: W97
    spec: VELDO-0134
    title: Accept a repository's architecture contract by a signed owner command
    feature_refs: [F3]
    depends_on: [VELDO-0053]
    order: 11134
    release: 1
    stage: 1
  - item: W98
    spec: VELDO-0135
    title: Enrolled work is offered from its authoritative floor state, not the spec status line
    feature_refs: [F3]
    depends_on: [VELDO-0049, VELDO-0052]
    order: 11135
    release: 1
    stage: 1
  - item: W99
    spec: VELDO-0136
    title: Tell the owner to reply to the request when an answer does not reply to a presentation
    feature_refs: [F5]
    depends_on: [VELDO-0065, VELDO-0066]
    order: 13136
    release: 1
    stage: 3

  - item: W100
    spec: VELDO-0140
    title: A standing answer delegation the owner renews, and no silent refusal of his answers
    feature_refs: [F5]
    depends_on: [VELDO-0025, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0073]
    order: 13140
    release: 1
    stage: 3
  - item: W101
    spec: VELDO-0141
    title: Every worker run's full live execution record, served for the UI's live terminal view
    feature_refs: [F4, F9]
    depends_on: [VELDO-0039, VELDO-0043, VELDO-0045, VELDO-0060, VELDO-0061, VELDO-0130]
    order: 15141
    release: 1
    stage: 5
  - item: W102
    spec: VELDO-0142
    title: Every repository is bound to exactly one Git identity, configured at setup, and every commit the factory makes for it is authored as that identity
    feature_refs: [F3]
    depends_on: [VELDO-0028, VELDO-0042, VELDO-0056, VELDO-0057, VELDO-0144, VELDO-0148]
    order: 15142
    release: 1
    stage: 5
  - item: W103
    spec: VELDO-0143
    title: A repository the owner asks for in chat is created or adopted and bound to a new project on his one answer
    feature_refs: [F6]
    depends_on: [VELDO-0028, VELDO-0029, VELDO-0047, VELDO-0068, VELDO-0076, VELDO-0088, VELDO-0089, VELDO-0126, VELDO-0132, VELDO-0142, VELDO-0149, VELDO-0150, VELDO-0152, VELDO-0153, VELDO-0154, VELDO-0161, VELDO-0162]
    order: 15143
    release: 1
    stage: 5
  - item: W104
    spec: VELDO-0144
    title: MCP servers defined once as versioned catalog records, with credentials only in the host OS keystore
    feature_refs: [F7]
    depends_on: [VELDO-0039, VELDO-0047, VELDO-0060, VELDO-0061, VELDO-0130]
    order: 15144
    release: 1
    stage: 5
  - item: W105
    spec: VELDO-0145
    title: The UI shell, the live run terminal and the decisions screen on phone and desktop
    feature_refs: [F9]
    depends_on: [VELDO-0130, VELDO-0141]
    order: 15145
    release: 1
    stage: 5
  - item: W108
    spec: VELDO-0148
    title: A land refused because another factory moved main is re-landed on the new tip, re-merged and re-gated, and nothing ever forces
    feature_refs: [F3]
    depends_on: [VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0154]
    order: 15148
    release: 1
    stage: 5
  - item: W109
    spec: VELDO-0149
    title: A project activates on any repository this domain adopted, by the owner's signed command or by his settled answer
    feature_refs: [F6]
    depends_on: [VELDO-0029, VELDO-0068, VELDO-0076]
    order: 14149
    release: 1
    stage: 4
  - item: W110
    spec: VELDO-0150
    title: An objective proposed from the project owner's own message is accepted by that message, and any other is still presented
    feature_refs: [F6]
    depends_on: [VELDO-0066, VELDO-0077, VELDO-0126]
    order: 14150
    release: 1
    stage: 4
  - item: W111
    spec: VELDO-0151
    title: A team may name specialist roles beyond the four required ones, and every role names its capability configuration and its kind
    feature_refs: [F7]
    depends_on: [VELDO-0089, VELDO-0127]
    order: 15151
    release: 1
    stage: 5
  - item: W112
    spec: VELDO-0152
    title: Intake decides a project only from a ticket key or the request's project field, and the factory project's PM routes every other message to a new project, an existing project or one question
    feature_refs: [F5]
    depends_on: [VELDO-0076, VELDO-0088, VELDO-0126, VELDO-0128, VELDO-0130, VELDO-0154]
    order: 15152
    release: 1
    stage: 5
  - item: W106
    spec: VELDO-0146
    title: Work of several units gets a separate elaboration run and a second PM cycle that stages the units against the published requirements
    feature_refs: [F7]
    depends_on: [VELDO-0085, VELDO-0088, VELDO-0091, VELDO-0154]
    order: 15146
    release: 1
    stage: 5
  - item: W107
    spec: VELDO-0147
    title: The Mac legs of the engine, account, capability, execution record and credential qualifications built on Linux first
    feature_refs: [F2]
    depends_on: [VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0124, VELDO-0125, VELDO-0127, VELDO-0141, VELDO-0144, VELDO-0155, VELDO-0156, VELDO-0158]
    order: 15147
    release: 1
    stage: 5
  - item: W113
    spec: VELDO-0153
    title: Every push the factory makes for a repository authenticates with its Git identity alone, to a remote under that identity's owner
    feature_refs: [F3]
    depends_on: [VELDO-0056, VELDO-0057, VELDO-0142, VELDO-0144]
    order: 15153
    release: 1
    stage: 5
  - item: W114
    spec: VELDO-0154
    title: The factory loop runs inside the authority service, woken only by commits, run ends and account resets, and re-dispatches or asks the owner at an account limit
    feature_refs: [F4]
    depends_on: [VELDO-0039, VELDO-0047, VELDO-0062, VELDO-0064, VELDO-0076, VELDO-0129, VELDO-0141, VELDO-0160]
    order: 15154
    release: 1
    stage: 5
  - item: W115
    spec: VELDO-0155
    title: Every Claude Code run starts on the everything-off baseline, behind the paid-API guard and the environment strip
    feature_refs: [F4]
    depends_on: [VELDO-0039, VELDO-0060]
    order: 11155
    release: 1
    stage: 1
  - item: W116
    spec: VELDO-0156
    title: Every Codex run starts on the everything-off baseline, behind the paid-API guard and the environment strip
    feature_refs: [F4]
    depends_on: [VELDO-0039, VELDO-0061]
    order: 11156
    release: 1
    stage: 1
  - item: W117
    spec: VELDO-0157
    title: The capability items a staffing choice assigns load with that run, and no other when-assigned item does
    feature_refs: [F7]
    depends_on: [VELDO-0090, VELDO-0125, VELDO-0127, VELDO-0147]
    order: 15157
    release: 1
    stage: 5
  - item: W118
    spec: VELDO-0158
    title: Each Linux run receives exactly its servers' credentials, resolved from the keystore just before spawn and added to the run's redaction set
    feature_refs: [F7]
    depends_on: [VELDO-0039, VELDO-0060, VELDO-0061, VELDO-0141, VELDO-0144, VELDO-0155, VELDO-0156]
    order: 15158
    release: 1
    stage: 5
  - item: W119
    spec: VELDO-0159
    title: The owner defines an MCP server and sets its credential in a minimal UI form, whose credential field is write-only
    feature_refs: [F9]
    depends_on: [VELDO-0144, VELDO-0145]
    order: 15159
    release: 1
    stage: 5
  - item: W120
    spec: VELDO-0160
    title: Work runs on every registered subscription account at once, moves off an account at its limit, and a limited run is classified and decided re-run or ask
    feature_refs: [F4]
    depends_on: [VELDO-0036, VELDO-0062]
    order: 11160
    release: 1
    stage: 1
  - item: W121
    spec: VELDO-0161
    title: A repository the owner names is adopted under one identity on his settled answer and taken on by the running factory without a restart
    feature_refs: [F6]
    depends_on: [VELDO-0028, VELDO-0029, VELDO-0047, VELDO-0068, VELDO-0142, VELDO-0153]
    order: 15161
    release: 1
    stage: 5
  - item: W122
    spec: VELDO-0162
    title: The owner saves capability configuration revisions, team revisions and the default team through typed API routes the authority executes, and a team revision becomes current on his own authenticated save or on his settled answer to another member's proposal
    feature_refs: [F7]
    depends_on: [VELDO-0064, VELDO-0068, VELDO-0089, VELDO-0127, VELDO-0130, VELDO-0151, VELDO-0152]
    order: 15162
    release: 1
    stage: 5
  - item: W123
    spec: VELDO-0163
    title: The owner writes a role's capability configuration and a project's team roles in a minimal UI form
    feature_refs: [F9]
    depends_on: [VELDO-0144, VELDO-0145, VELDO-0162]
    order: 15163
    release: 1
    stage: 5

regression:
  journeys:
    - id: RJ1
      title: Release 1 full installed journey from a Telegram message pointing at a Jira ticket, fetched through the Atlassian catalog server, through the LangGraph PM, Linux and Mac workers on at least two subscription accounts watched in the live terminal, proof, review, exact landing and owner completion
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
services authorize and commit. Independent review, authentic answers, pre-invocation subscription usage caps and
publication of exactly the tested tree are part of the function. The owner's standing rule is
logged-in Claude Code and Codex subscriptions only, with no paid model API or per-call price.
0036/0060/0061/0062 govern invocation, wall-time, CLI-reported token/message caps and exposed
subscription rate-limit windows; check before each invocation, stop at the cap and retain
unknown usage conservatively. Historical monetary-maxima language in the design is superseded
by this subscription usage model.

Revision 4 records the owner's approval on 2026-09-25 of the operating-model design,
[docs/design/PLAN-0019-operating-model-design.md](../docs/design/PLAN-0019-operating-model-design.md)
(Telegram 29162, "all 6 are yes"), and his answer to its one open decision (29163, "yes, Codex and
Claude can read creds"). Work starts from a message that may point at a Jira ticket; a project manager
whose reasoning runs as ordinary worker runs coordinates every piece of work through one default
pipeline; the factory loop inside the authority service offers each next station; MCP servers live in
a versioned catalog with their credentials in the OS keystore; new repositories come from chat under
one Git identity each; every run keeps a full live execution record the owner watches as a terminal;
work spreads over every logged-in account; and a land re-lands when another person's factory moved
main. Each person runs their own factory. Separating the engine login from worker tools is Release 2
hardening for both engines.

## Releases and order

Release 1 is delivered in six stages. Within each stage `depends_on` is the actual functional DAG;
`order` is only a tie-breaker. Packages A-H remain feature labels, not completion barriers. A later
stage may integrate an earlier service without making that service depend on the final journey.

1. **Delivery.** Claims and explicit dispatch, a real authenticated IPC request applied to the real
   configured SQLite store, local service exclusion, snapshots/materialization, reservations,
   Linux worker groups, isolated clones, live Claude Code and Codex adapters, real build/review
   wiring, proof, shared eligibility, isolated gate observations, exact-tip publication and journal
   completion. Since the revision 4 review the factory loop (VELDO-0154, split from VELDO-0129) and
   the re-land (VELDO-0148) are stage 5 items, because the loop reads the stage 5 execution record. Provision minimal accepted owner/project/admission records for integration checks.
2. **Mac and relay.** Qualify the Mac's simple worker lifecycle and connect its workers through
   built VELDO-0108 to the Linux authority. Route macOS/iOS work only to a qualified Mac.
3. **Telegram decisions.** Common message intake, actual Telegram enrollment and send/receive,
   exact versioned presentations, canonical owner attribution, atomic settlements and governing
   decision bindings, clean decision-stop resumption, ordinary progress/stop/completion reports.
4. **Projects and the LangGraph project manager.** Project/owner/charter and objective acceptance,
   prioritized backlog and published specification decomposition, bounded PM elaboration, versioned
   teams and exact agent/tool/MCP configuration, specialist matching and typed authorized proposals.
   Ordinary "fix this bug" work runs the operating-model design's default pipeline like any other
   work (revision 4 moves VELDO-0080 to Release 2); an objective from the owner's own message is
   accepted and admitted at default priority by that message unless the PM raises a question.
   PM proposals take effect one owning command at a time with a named stop (VELDO-0092's atomic
   groups are Release 2).
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

**Build order inside Release 1 (revision 4).** The stage numbers above group functions and keep every
dependency on the same or an earlier stage. The order in which the remaining Release 1 items are
built follows section 12 of the operating-model design, so the owner starts using the factory at the
end of its second stage: watch real runs first (0062 and its account pool, VELDO-0160; 0060 and 0061, each with its baseline and guards,
VELDO-0155 and VELDO-0156; 0141; 0129 and the factory loop VELDO-0154; 0145; 0128), then
"please do BCG-123" to a landed change (0089, 0140, 0078; 0079 with the acceptance amendment,
VELDO-0150; 0144 and its delivery to a run, VELDO-0158; the MCP server and credential form,
VELDO-0159, moved earlier from 0131 so the owner can enter the Atlassian credential in this stage; 0127
with the specialist-role amendment, VELDO-0151; the configuration and team routes, VELDO-0162, and the
role and team form, VELDO-0163, so the owner can give a role the Atlassian server and put it in a team
in this stage; a thin 0088 that stages one
unit; and the 0057 re-land, VELDO-0148), then the rest of the MVP (0124 and 0125, then their Mac legs,
VELDO-0147; 0085 and 0091; 0090 with load modes and the `when assigned` leg of 0127 AC4, VELDO-0157;
the rest of 0088, VELDO-0146; 0142 and its push half, VELDO-0153; 0143 with its adoption, VELDO-0161, and
the 0076 and 0126 amendments, VELDO-0149 and VELDO-0152; the rest of 0131; 0059). Section 12 lists 0091 before 0090,
and its dependency paragraph says 0091 needs 0090, so 0091 is built once 0090 has landed. A
specification ships whole and the
run-check refuses one whose dependencies are not shipped, so no specification built before the Mac
stage carries a Mac leg: the Mac legs of VELDO-0060, 0061, 0062, 0127, 0141 and 0144 are VELDO-0147.
The amendments of the landed VELDO-0057, 0076, 0077, 0089 and 0126 are VELDO-0148 to VELDO-0152, each
depending on the specification it amends.

Release 2 delivers robustness and recovery: off-host acknowledgement, authority generations and
fencing, clock follow-ups, recovery commands, checkpoint isolation and restoration, replay and lost
acknowledgements, governor failure matrices, interrupted decisions and operational recovery. Revision 4
adds three items: typed proposal groups that apply all or nothing (W77, VELDO-0092), the ordinary
defect path of VELDO-0080 as its own work item (W65), and separating the engine login from worker
tools for Claude Code and Codex (the former login clauses of VELDO-0060 AC4, VELDO-0061 AC4,
VELDO-0062 AC1 and R45).
Unknown effects remain stopped in Release 1 with original dispatch identity and unknown usage reservations;
a process exit is not evidence that a remote operation did not happen. Ordinary unavailable-service
checks and actual IPC-to-store integration are required now without claiming the broader follow-up
qualification matrices have been proven.

Release 3 adds governance depth: full regression receipt consumers, adversarial decision review
and tripwires, trusted automatic defect reproduction/admission, advanced policy work classes and
quarantine, standing/emergency admission, readmission debt,
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
| W44 | VELDO-0059 | 1 | 6; RJ1 and dependencies amended in revision 4 |
| W45 | VELDO-0060 | 1 | 1; amended in revision 4 |
| W46 | VELDO-0061 | 1 | 1; amended in revision 4 |
| W47 | VELDO-0062 | 1 | 1; amended in revision 4 |
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
| W64 | VELDO-0079 | 1 | 4; admission by his message, revision 4 |
| W65 | VELDO-0080 | 2 | - (revision 4); automatic reproduction/admission remains R3 |
| W66 | VELDO-0081 | 3 | - |
| W67 | VELDO-0082 | 3 | - |
| W68 | VELDO-0083 | 3 | - |
| W69 | VELDO-0084 | 3 | - |
| W70 | VELDO-0085 | 1 | 4 |
| W71 | VELDO-0086 | 3 | - |
| W72 | VELDO-0087 | 3 | - |
| W73 | VELDO-0088 | 1 | 5; one-unit work, amended in revision 4 |
| W74 | VELDO-0089 | 1 | 4 |
| W75 | VELDO-0090 | 1 | 5; amended in revision 4 |
| W76 | VELDO-0091 | 1 | 5; amended in revision 4 |
| W77 | VELDO-0092 | 2 | - (revision 4) |
| W78 | VELDO-0093 | 2 | - |
| W79 | VELDO-0094 | 4 | - |
| W80 | VELDO-0095 | 4 | - |
| W81 | VELDO-0096 | 4 | - |
| W82 | VELDO-0097 | 2 | - |
| W83 | VELDO-0098 | 4 | - |
| W87 | VELDO-0124 | 1 | 2 |
| W88 | VELDO-0125 | 1 | 2 |
| W89 | VELDO-0126 | 1 | 3 |
| W90 | VELDO-0127 | 1 | 5; amended in revision 4 |
| W91 | VELDO-0128 | 1 | 3 |
| W92 | VELDO-0129 | 1 | 1; AC4 to AC6 added in revision 4 and split into VELDO-0154 by its review |
| W93 | VELDO-0130 | 1 | 5 |
| W94 | VELDO-0131 | 1 | 5; amended in revision 4; its server and credential form moved to VELDO-0159 and its role form to VELDO-0163 |
| W95 | VELDO-0132 | 1 | 4 |
| W96 | VELDO-0133 | 1 | 3 |
| W97 | VELDO-0134 | 1 | 1 |
| W98 | VELDO-0135 | 1 | 1 |
| W99 | VELDO-0136 | 1 | 3 |
| W100 | VELDO-0140 | 1 | 3 |
| W101 | VELDO-0141 | 1 | 5 |
| W102 | VELDO-0142 | 1 | 5 |
| W103 | VELDO-0143 | 1 | 5 |
| W104 | VELDO-0144 | 1 | 5 |
| W105 | VELDO-0145 | 1 | 5 |
| W108 | VELDO-0148 | 1 | 5 |
| W109 | VELDO-0149 | 1 | 4 |
| W110 | VELDO-0150 | 1 | 4 |
| W111 | VELDO-0151 | 1 | 5 |
| W112 | VELDO-0152 | 1 | 5 |
| W106 | VELDO-0146 | 1 | 5 |
| W107 | VELDO-0147 | 1 | 5 |
| W113 | VELDO-0153 | 1 | 5 |
| W114 | VELDO-0154 | 1 | 5 |
| W115 | VELDO-0155 | 1 | 1 |
| W116 | VELDO-0156 | 1 | 1 |
| W117 | VELDO-0157 | 1 | 5 |
| W118 | VELDO-0158 | 1 | 5 |
| W119 | VELDO-0159 | 1 | 5; the server and credential form, moved earlier from VELDO-0131 |
| W120 | VELDO-0160 | 1 | 1 |
| W121 | VELDO-0161 | 1 | 5 |
| W122 | VELDO-0162 | 1 | 5; the configuration and team routes |
| W123 | VELDO-0163 | 1 | 5; the role and team form, moved earlier from VELDO-0131 |

## Related baseline and follow-up disposition

These standalone or PLAN-0020 items retain their existing binding and status; they are not silently
moved into PLAN-0019's work graph. VELDO-0099 is existing installation evidence usable by Release 1;
VELDO-0100's confinement qualification belongs to Release 2. VELDO-0101 through VELDO-0106 remain
PLAN-0020 review machinery, existing evidence rather than new MVP runtime gates. VELDO-0110 is an
existing reader foundation. VELDO-0111 through VELDO-0117, VELDO-0121 and VELDO-0122 are Release 2
qualification follow-ups; the actual single-domain store connection from 0115 is required in 0047
now. VELDO-0118 through VELDO-0120 and VELDO-0123 are Release 2 parser/gate qualification, including
already recorded evidence. A release assignment does not undo code or change a status field.
VELDO-0137, VELDO-0138 and VELDO-0139 are standalone items built on 2026-09-25 that Release 1 reuses:
the policy digest reader, the authority service running the Telegram ingress, and factory setup on a
host. W100's VELDO-0140 also builds on VELDO-0138, and W102's VELDO-0142, W103's VELDO-0143 and W121's
VELDO-0161 on VELDO-0139's setup; those edges stay in the specifications because a plan edge must name a work item.

## Revision history and dependency basis

2026-09-22: revision 3 replaces package completion barriers with release-scoped functional edges,
amends C3/C5/C7/C10/C11/C12/NG3 and adds C14-C17 under the owner rulings quoted in C3, C5, C10, C12, NG3 and C15, and the
dated owner decisions recorded in C7 and C14-C17. It preserves
C13's commit-pinned, named, read-only attachments. The analyses `ask-20260922-213601.md` sections 1-4
and `ask-20260922-212450.md` in the owner's research/codex-reviews directory supply the trim and
consumption basis; the later Mac, UI/API and no-Jira decisions override their narrower suggestions.
VELDO-0035, 0054 and 0069 retain consumed normal functions; 0053 retains required architecture entry
checks. 0089 consumes retained engineering review, not deferred 0070 adversarial decision review.
0047 incorporates local exclusion from 0030 and normal real-store wiring from 0115; 0088 incorporates
ordinary cycle serialization from 0093. Their broader matrices keep their later release allocation.
Nine new draft specifications, VELDO-0124 through VELDO-0132, fill the host, routing, intake,
capability, reporting, live wiring, API, UI and workflow-definition concerns in this same graph. The final writing audit lives in proof/plan-0019-rev3/README.md.

2026-09-23: W96 adds VELDO-0133 as a Release 1 stage 3 draft. It answers VELDO-0064's open question
under owner Telegram 28934 (ask the person who declined or canceled) and 28936 (ask the project
owner when no person did), and depends on VELDO-0126 for the intake of a free-text disposition.

2026-09-23: W97 adds VELDO-0134 as a Release 1 stage 1 draft. VELDO-0053 reads a store record
architecture:<repository> that makes the architecture contract required, and nothing wrote it, so
whether the contract was required still came from the workspace's editable policy (R50). W97 adds
the signed owner command that is its only writer and the written schema both writer and reader
are checked against, and depends on VELDO-0053.

2026-09-24: W98 adds VELDO-0135 and W99 adds VELDO-0136 as Release 1 drafts, both from scoped reviews
that night. W98: the frontier and the work loop read the spec status line, which VELDO-0049 stopped
writing for enrolled work, so the enrolled journey stalls after build acceptance. W99: an owner who answers
without pressing Reply gets silence (VELDO-0066's review).

2026-09-25: revision 4, approved by the owner on Telegram 29162, 29163 and 29165. In 29162 ("all 6 are
yes") he approved the operating-model design docs/design/PLAN-0019-operating-model-design.md at
12879d3, and in 29163 ("yes, Codex and Claude can read creds") he answered its section 15 yes for both
engines, and in 29165 ("yes") he confirmed that answer. The revision applies that design's section
10(e). W65 (VELDO-0080) and W77 (VELDO-0092) move to Release 2. W100 to W105 add VELDO-0140 and VELDO-0141 (both written standalone on
2026-09-25 and now bound here) and the new drafts VELDO-0142 (Git identities), VELDO-0143 (a repository
from chat), VELDO-0144 (the MCP catalog and OS keystore) and VELDO-0145 (the UI shell, live terminal
and decisions screen). VELDO-0059 drops VELDO-0080 and VELDO-0092 and depends on VELDO-0140 to
VELDO-0145. C1 names the operating-model design; O4 and R45 move login separation to Release 2 for
both engines; the controlling design gains dated revision 4 notes, and R75 states the per-person
deployment as its deployment view; RJ1 starts from a Telegram message pointing at a Jira ticket,
fetched through the Atlassian catalog server, uses at least two accounts and is watched in the live
terminal. The amended specifications are VELDO-0059, 0060, 0061, 0062, 0079, 0088,
0090, 0091, 0127, 0129, 0131 and 0141, each with the criterion text the design gives and
a History entry; VELDO-0141 moves to ready on the approval. VELDO-0057, VELDO-0076, VELDO-0077, VELDO-0089
and VELDO-0126 have landed, so their amendments are their own specifications that depend on them:
W108's VELDO-0148 (the re-land), W109's VELDO-0149 (activation on an adopted repository, from a settled
answer), W110's VELDO-0150 (acceptance by his own message), W111's VELDO-0151 (specialist roles) and
W112's VELDO-0152 (ticket keys and new projects at intake); each landed specification keeps its landed
text. The dependency changes the amendments
imply are recorded as edges: VELDO-0148 on VELDO-0129 (the loop offers the re-land), VELDO-0129 on
VELDO-0039, VELDO-0047 and VELDO-0062 (the loop runs the Runner in the service and sets account reset
timers) and on VELDO-0064 and VELDO-0141 (it asks the owner about an account-limited run whose record
shows a write through an MCP server, so it moves to stage 5 with VELDO-0148), VELDO-0127 on VELDO-0144 (roles refer to catalog servers) and VELDO-0131 on VELDO-0141 to
VELDO-0145 (its new rows). Because VELDO-0144 adds an API route and so depends on VELDO-0130, it is
stage 5, and VELDO-0127, VELDO-0090 and VELDO-0091, which depend on it in turn, move from stage 4 to
stage 5 so no dependency points at a later stage; the build order follows the design's section 12 and
is stated under Releases and order. Every PLAN-0019 specification pulled at revision 3 is re-pulled at
revision 4. The writing audit is proof/plan-0019-rev4/README.md.

2026-09-25: revision 4 review fixes, within revision 4 and without changing what the owner approved,
cutting a function or moving anything else to Release 2. A specification ships whole and the run-check
refuses one whose dependencies are not shipped, so work the design's critical path builds in different
stages is split: VELDO-0088 is the thin one-unit PM of stage 2 and W106's VELDO-0146 the several-unit
work of stage 3, and the Mac legs of VELDO-0060, 0061, 0062, 0127, 0141 and 0144 are W107's VELDO-0147,
built after VELDO-0124 and VELDO-0125. The landed VELDO-0057, 0076, 0077, 0089 and 0126 keep their landed
text and their amendments are W108 to W112 (VELDO-0148 to VELDO-0152), as recorded above; W100's
VELDO-0140, which also landed, is bound here with no change to its criteria. VELDO-0142 keeps the identity
and the author, and W113's VELDO-0153 the identity push profile and the remote owner check. VELDO-0141
AC3 is the record route's contract and VELDO-0145 AC2 the screen. VELDO-0062 AC6 decides re-run or ask
over a record and VELDO-0129 AC6 carries the decision out, which, with the record VELDO-0129 now reads,
moves W92 (VELDO-0129) and W108 (VELDO-0148) to stage 5; W73 (VELDO-0088) moves to stage 5 because the
PM role's configuration comes from VELDO-0151. The writing audit, proof/plan-0019-rev4/README.md, lists
each fix.

2026-09-25: revision 4 review, one concern per specification. VELDO-0129 held two concerns in six
criteria, so its AC4 to AC6 (the factory loop's wake sources with no polling in the loop, a receiver that
dies, and the re-dispatch or the question to the owner at an account limit) are W114's VELDO-0154, stage
5, with their text and falsifiers unchanged. W92 keeps real build and review through the Runner and
returns to stage 1, because none of its remaining dependencies is later. W73 (VELDO-0088) and W108
(VELDO-0148) depend on VELDO-0154 in place of VELDO-0129, where the loop is what they meant, and W44
(VELDO-0059), W103 (VELDO-0143) and W106 (VELDO-0146) add it.

2026-09-25: revision 4, third review, within revision 4 and without changing what the owner approved,
cutting a function or moving anything else to Release 2. VELDO-0060 AC5 and VELDO-0061 AC5 bundled the
everything-off baseline, the paid-API guard and the environment strip under one falsifier that tested
only the paid-API guard, so each engine's three guards are one new draft, W115's VELDO-0155 (Claude
Code) and W116's VELDO-0156 (Codex), both stage 1 and built with their adapter as section 12's items 2
and 3 say, with one criterion and one falsifier per guard (the paid-API guard's removal and its stop are
two). They are per engine rather than one shared specification because the baseline and the stop are
each engine's own levers; the strip is the one trusted wrapper, and each reads back its own engine's
environment. W92 (VELDO-0129), W90 (VELDO-0127), W107 (VELDO-0147) and W44 (VELDO-0059) add both, so
nothing that ran behind the guards when they were part of the adapters runs without them now.
Section 12 builds VELDO-0127 in its second stage with every item `always` and the load modes in its
third with VELDO-0090 ("VELDO-0090 with load modes and VELDO-0127 AC4"), so VELDO-0127 AC4 keeps the
`always` leg and the `when assigned` leg is W117's VELDO-0157, stage 5, built with VELDO-0090 and
depending on it; the build-order paragraph under Releases and order now follows section 12's stage 3.
VELDO-0141 AC4 replaces the exact credential values a run resolved, but in stage 1 nothing supplies one,
so AC4 names the per-run set of resolved values and tests it with a planted resolver. Requiring the
keystore's values to enter that set would have made VELDO-0144 a fifth criterion, so VELDO-0144 keeps
defining servers and storing credentials (AC1 and AC2) and W118's VELDO-0158, stage 5 and built with it
as section 12's item 10, owns delivery at launch: VELDO-0144's former AC3 and AC4, unchanged, and a new
AC3 whose falsifier resolves a keystore value without adding it to the set. W90 (VELDO-0127), W107
(VELDO-0147) and W44 (VELDO-0059) add it.
At the end of section 12's second stage the owner had no way to enter the Atlassian credential: VELDO-0144
AC2 is the API route and the server form was part of VELDO-0131, built in the third stage. On the lead's
decision the form moves earlier: W119's VELDO-0159, stage 5, a minimal server form with a write-only
credential field depending on VELDO-0144 and VELDO-0145 and built in the second stage after VELDO-0144,
so "please do BCG-123" works at the end of that stage as the design promises. VELDO-0131's "MCP servers
and credentials" row no longer carries the form, which is not built twice, and W94 (VELDO-0131) and W44
(VELDO-0059) depend on VELDO-0159.
VELDO-0078 has landed and keeps its landed text at `plan_revision: 4` like the other landed
specifications, so its Notes still say ordinary defects (VELDO-0080) are executable in Release 1; since
revision 4 moved W65 (VELDO-0080) to Release 2, ordinary defects instead run the default pipeline like
any other work, after normal shaping, owner admission and priority, and that plan statement governs.
VELDO-0062 held six criteria, so the pool (its AC5) and the `account_limit` classification with the
re-run-or-ask decision (its AC6) are W120's VELDO-0160, stage 1, built with VELDO-0062 as section 12's
item 1; AC6 becomes two criteria with a falsifier each, and the fixture record form is written in the
specification because VELDO-0141 and VELDO-0144 come later. W114 (VELDO-0154), which carries the
decision out, W94 (VELDO-0131), whose usage row shows the windows, and W44 (VELDO-0059) depend on it.
W64 (VELDO-0079) depends on W110's VELDO-0150, whose acceptance by his own message is what its AC2
admits, and W114 (VELDO-0154) on W61's VELDO-0076, whose pause its AC1 respects; VELDO-0154 states that
with no catalog every MCP call asks the owner, instead of depending on VELDO-0144, which section 12 builds
after it.
Two criteria claimed something with no falsifier of their own. VELDO-0154 AC1's "no timer other than an
account reset starts a pass" is new AC4 with its own. VELDO-0143 AC3's "taken on by the running service
without a restart" needed one too, which would have given VELDO-0143 five criteria, so adoption, with
the signer scope and the no-restart criterion, is W121's VELDO-0161, stage 5, built with VELDO-0143 as
section 12's item 19; W103 (VELDO-0143) and W44 (VELDO-0059) depend on it.

2026-09-25: revision 4, fourth review, within revision 4 and without changing what the owner approved,
cutting a function or moving anything else to Release 2. At the end of section 12's second stage the
owner could not give a role the Atlassian server: VELDO-0151 refuses a team whose roles have no accepted
VELDO-0127 configuration, but the API's route table has only the workflow save in its configuration
family, VELDO-0130's History names team and agent configuration edits as having no route, and the role
form was part of VELDO-0131, built in the third stage. W122's VELDO-0162 adds the typed routes for
capability configuration revisions and team revisions, executed as VELDO-0127's revision command and
VELDO-0089's `propose`, and the request whose settled answer VELDO-0089's `amend` applies; W123's
VELDO-0163 is the minimal role and team form in the VELDO-0145 shell. Together they would have held five
criteria, so the routes and the form are two specifications, both stage 5 and built in the second stage
after VELDO-0127 and VELDO-0151, as VELDO-0159 is. VELDO-0131's "Team and agent/tool/MCP configuration"
row no longer carries the form, which is not built twice, and W94 (VELDO-0131) and W44 (VELDO-0059)
depend on both.
W118 (VELDO-0158) depends on W115's VELDO-0155 and W116's VELDO-0156, whose baselines generate the
configuration and environment it delivers credentials into, and states the form of the dispatch
configuration it resolves, since VELDO-0127 is built after it.
VELDO-0160 AC1 held four claims under one falsifier, so AC1 keeps the concurrent isolated accounts and
the new AC4 carries moving off an exhausted account, adding one without a restart and the one-run bound
while usage is unknown, each with its own mutant.
W117 (VELDO-0157) carries the Mac leg of the `when assigned` items and depends on W88's VELDO-0125 and
W107's VELDO-0147; it cannot be in VELDO-0147, which W75's VELDO-0090 depends on, without a cycle.
VELDO-0143 AC3 activated a new project with a default team template that VELDO-0089 does not define, so
VELDO-0162 AC4, built in the second stage, defines the default team, and W103 (VELDO-0143) depends on it.

2026-09-26: within revision 4, the owner's decision on new projects (Telegram 29186, 29187 and 29191): a
new project is recognized by the factory project's PM, a Claude Code or Codex run that reads his text,
never by a keyword rule. W112's VELDO-0152 decides at intake only by a ticket key or the request's project
field, passes a project name in the text to the PM as a hint, sends every other message to the factory
project's inbox, and applies the PM's route (a new project, an existing project, or one question to the
owner when it is unclear). It now depends on W73's VELDO-0088 (the PM run), W114's
VELDO-0154 (the loop that starts its cycle), W91's VELDO-0128 (the progress report) and W93's VELDO-0130
(the read the UI uses), so W112 moves from stage 4 to stage 5; none of them depends on it.
