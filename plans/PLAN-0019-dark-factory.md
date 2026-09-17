---
schema: veldo.plan/v1
id: PLAN-0019
title: Dark Factory project coordination inside Veldo
kind: mvp
status: draft
revision: 1
owner: dmitry
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
      No new management console, unverified Jira board changes, modifications to published prose, or
      material from client engagements.

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
      The four R03 architectural recommendations remain open for Dmitry: SQLite authority with
      signed Git replica, off-host acknowledgement before success, Linux systemd cgroup v2 runner,
      and isolated clones with a shared object cache. The guardian recommendation is not Dmitry's
      approval.
  - id: C4
    text: >
      R21 permits one local SQLite authority at <git-common-dir>/veldo/control/control.sqlite3 per
      domain on a qualified local filesystem. LangGraph owns only isolated checkpoint tables; model
      processes receive no database access. Cross-namespace writes and indirect writes refuse, and
      domain history remains valid when checkpoints are removed.
  - id: C5
    text: >
      R35 preserves stdlib_only_enforcement for validators, authorization, gate imports, journal
      replay, and recovery. A pinned, hashed, licensed execution runtime installs separately, with
      compatibility proof and complete distribution inventory before the first slice.
  - id: C6
    text: >
      R53 places implementation in canonical engine/ with byte-identical pack synchronization.
      Domain contracts accept plain versioned data and import neither LangGraph nor worker engines.
      Only the store commits, the runner launches, the lander publishes source, and the Evidence
      Service signs observations. Every asset has an explicit distribution disposition.
  - id: C7
    text: >
      Dmitry's 2026-09-16 22:38 ruling supersedes PLAN-0016's no-chat path and v2's tracker-first
      answer surface. Every enrolled input surface, including Telegram chat, Jira, signed CLI, and
      email when enrolled, is a decision surface. The kernel master-and-proxies principle requires
      one settlement in Veldo authority, originating-channel attribution, and the presentation the
      person saw bound to every answer. A channel is never a second record.
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
      Package A defines contracts without installing runtime authority. VELDO-0015 already
      implements clock stand-down at the baseline; inspect it rather than infer completeness from
      status. Its task-reporting, claim-refusal propagation, and status-display follow-ups belong to
      Package B before C.
  - id: C11
    text: >
      Every implementation item requires its own ready specification, three or four falsifiable
      criteria, proof, independent review, and green gate. Live provider proof belongs to D; real
      decision-channel and interrupted-settlement proof belongs to E, never to C's approval
      fixtures. Activation is separate from source landing.

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

work:
  - item: W1
    spec: VELDO-0016
    title: Decision records and effective policy amendments
    feature_refs: [F1]
    depends_on: []
    order: 101
  - item: W2
    spec: VELDO-0017
    title: Entity identity and lifecycle schemas
    feature_refs: [F1]
    depends_on: []
    order: 102
  - item: W3
    spec: VELDO-0018
    title: Release and behavior-floor integration contracts
    feature_refs: [F1]
    depends_on: [VELDO-0017]
    order: 103
  - item: W4
    spec: VELDO-0019
    title: Combined dependency graph and decision observation rules
    feature_refs: [F1]
    depends_on: [VELDO-0017, VELDO-0018]
    order: 104
  - item: W5
    spec: VELDO-0020
    title: Signing and authority contracts for enrolled channels
    feature_refs: [F1]
    depends_on: [VELDO-0016, VELDO-0017]
    order: 105
  - item: W6
    spec: VELDO-0021
    title: Completion and executable eligibility predicates
    feature_refs: [F1]
    depends_on: [VELDO-0018, VELDO-0019, VELDO-0020]
    order: 106
  - item: W7
    spec: VELDO-0022
    title: Section 2 admission semantics
    feature_refs: [F1]
    depends_on: [VELDO-0017, VELDO-0020]
    order: 107
  - item: W8
    spec: VELDO-0023
    title: Atomic journaled commands and deterministic replay
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022]
    order: 208
  - item: W9
    spec: VELDO-0024
    title: Signed Git replication and off-host acknowledgement
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023]
    order: 209
  - item: W10
    spec: VELDO-0025
    title: Authenticated membership and scoped delegation
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023]
    order: 210
  - item: W11
    spec: VELDO-0026
    title: Revocation and authorization rechecks
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0025]
    order: 211
  - item: W12
    spec: VELDO-0027
    title: Protected signing and key lifecycle
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0025]
    order: 212
  - item: W13
    spec: VELDO-0028
    title: Protected effect execution and atomic nonce consumption
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0026, VELDO-0027]
    order: 213
  - item: W14
    spec: VELDO-0029
    title: Explicit repository enrollment and authority routing
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0025]
    order: 214
  - item: W15
    spec: VELDO-0030
    title: Exclusive leadership and authority-generation fencing
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0029]
    order: 215
  - item: W16
    spec: VELDO-0031
    title: Authority-backed claims and claim-generation fencing
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0030]
    order: 216
  - item: W17
    spec: VELDO-0032
    title: Clock uncertainty in task reporting
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0031]
    order: 217
  - item: W18
    spec: VELDO-0033
    title: Clock claim-refusal propagation through execution and landing
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0031]
    order: 218
  - item: W19
    spec: VELDO-0034
    title: Clock uncertainty in the status display
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0031]
    order: 219
  - item: W20
    spec: VELDO-0035
    title: Complete read-set validation and authoritative snapshots
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023]
    order: 220
  - item: W21
    spec: VELDO-0036
    title: Durable capacity and spend reservations
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023]
    order: 221
  - item: W22
    spec: VELDO-0037
    title: Atomic specification alias allocation and document publication
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023]
    order: 222
  - item: W23
    spec: VELDO-0038
    title: Effect-specific reconciliation and recovery commands
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0024, VELDO-0028, VELDO-0030, VELDO-0031, VELDO-0035, VELDO-0036]
    order: 223
  - item: W24
    spec: VELDO-0039
    title: Durable dispatch acceptance and launch records
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0024, VELDO-0031, VELDO-0035, VELDO-0036, VELDO-0038]
    order: 224
  - item: W25
    spec: VELDO-0040
    title: Provider-neutral process supervision and descendant containment
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0039]
    order: 225
  - item: W26
    spec: VELDO-0041
    title: Independent heartbeat, bounded stopping, and safe capacity retirement
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0040]
    order: 226
  - item: W27
    spec: VELDO-0042
    title: Isolated worker clones and pinned read-only shared object cache
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0029, VELDO-0031]
    order: 227
  - item: W28
    spec: VELDO-0043
    title: Replaceable LangGraph execution adapter
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0035]
    order: 228
  - item: W29
    spec: VELDO-0044
    title: Checkpoint namespace isolation and bounded contention
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0043]
    order: 229
  - item: W30
    spec: VELDO-0045
    title: Pinned isolated runtime, dependency licenses, and distribution inventory
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0043, VELDO-0044]
    order: 230
  - item: W31
    spec: VELDO-0046
    title: Durable wake-up, cursor replay, and notification delivery
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024]
    order: 231
  - item: W32
    spec: VELDO-0047
    title: Authority service installation, startup, stop, and absent-service behavior
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0029, VELDO-0030, VELDO-0040, VELDO-0041, VELDO-0046]
    order: 232
  - item: W33
    spec: VELDO-0048
    title: Integrity verification, replica restoration, and host-replacement fencing
    feature_refs: [F2]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0024, VELDO-0038, VELDO-0047]
    order: 233
  - item: W34
    spec: VELDO-0049
    title: Dispatch and tracker bridge consume authoritative state transitions
    feature_refs: [F3]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048]
    order: 334
  - item: W35
    spec: VELDO-0050
    title: Executor persists proof and performs complete contextual validation
    feature_refs: [F3]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0049]
    order: 335
  - item: W36
    spec: VELDO-0051
    title: Canonical event vocabulary and journal-derived publication
    feature_refs: [F3]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0049, VELDO-0050]
    order: 336
  - item: W37
    spec: VELDO-0052
    title: Shared eligibility in work, frontier, plan, direct executor, and review
    feature_refs: [F3]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0049]
    order: 337
  - item: W38
    spec: VELDO-0053
    title: Architecture failure handling at every eligibility entry
    feature_refs: [F3]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0052]
    order: 338
  - item: W39
    spec: VELDO-0054
    title: Decision-record dependency evaluation for the floor slice
    feature_refs: [F3]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0052]
    order: 339
  - item: W40
    spec: VELDO-0055
    title: Release regression receipt consumption
    feature_refs: [F3]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0052]
    order: 340
  - item: W41
    spec: VELDO-0056
    title: Disposable landing candidate construction and failure isolation
    feature_refs: [F3]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0050]
    order: 341
  - item: W42
    spec: VELDO-0057
    title: Exact-tip publication, lost acknowledgement recovery, and completion receipt
    feature_refs: [F3]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0054, VELDO-0055, VELDO-0056]
    order: 342
  - item: W43
    spec: VELDO-0058
    title: Gate-output isolation and exact tested-tree evidence
    feature_refs: [F3]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0056]
    order: 343
  - item: W44
    spec: VELDO-0059
    title: Installed end-to-end floor slice with fake model and real enforcement
    feature_refs: [F3]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058]
    order: 344
  - item: W45
    spec: VELDO-0060
    title: Claude Code production adapter qualification
    feature_refs: [F4]
    depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059]
    order: 445
  - item: W46
    spec: VELDO-0061
    title: Codex production adapter qualification
    feature_refs: [F4]
    depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059]
    order: 446
  - item: W47
    spec: VELDO-0062
    title: Provider credential separation and live usage accounting
    feature_refs: [F4]
    depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059]
    order: 447
  - item: W48
    spec: VELDO-0063
    title: Production governor and lifecycle failure qualification
    feature_refs: [F4]
    depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0060, VELDO-0061, VELDO-0062]
    order: 448
  - item: W49
    spec: VELDO-0064
    title: Assignment inbox and durable projections on enrolled input surfaces
    feature_refs: [F5]
    depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059]
    order: 549
  - item: W50
    spec: VELDO-0065
    title: Versioned presentation receipts for every enrolled channel
    feature_refs: [F5]
    depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0064]
    order: 550
  - item: W51
    spec: VELDO-0066
    title: Canonical channel attribution including platform-derived chat message, sender, and time
    feature_refs: [F5]
    depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0064]
    order: 551
  - item: W52
    spec: VELDO-0067
    title: Per-channel restricted edge signing and enrollment
    feature_refs: [F5]
    depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0066]
    order: 552
  - item: W53
    spec: VELDO-0068
    title: Atomic cross-channel settlement and principal-based quorum enforcement
    feature_refs: [F5]
    depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0065, VELDO-0066, VELDO-0067]
    order: 553
  - item: W54
    spec: VELDO-0069
    title: Governing decision binding, supersession, and eligibility updates
    feature_refs: [F5]
    depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0068]
    order: 554
  - item: W55
    spec: VELDO-0070
    title: Independent decision review bound to full framing and distinct principals
    feature_refs: [F5]
    depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0069]
    order: 555
  - item: W56
    spec: VELDO-0071
    title: Governing assumption observations and tripwire review flow
    feature_refs: [F5]
    depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0069, VELDO-0070]
    order: 556
  - item: W57
    spec: VELDO-0072
    title: PLAN-0016 tracker projection and canonical-history repair
    feature_refs: [F5]
    depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0065, VELDO-0066, VELDO-0068]
    order: 557
  - item: W58
    spec: VELDO-0073
    title: Per-channel live ingress activation and real sandbox qualification
    feature_refs: [F5]
    depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0067, VELDO-0072]
    order: 558
  - item: W59
    spec: VELDO-0074
    title: Interrupted and concurrent decisions across enrolled channels
    feature_refs: [F5]
    depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0073]
    order: 559
  - item: W60
    spec: VELDO-0075
    title: Andon delivery and authorized resumption through enrolled channels
    feature_refs: [F5]
    depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0068]
    order: 560
  - item: W61
    spec: VELDO-0076
    title: Project ownership, charter, lifecycle, and transfers
    feature_refs: [F6]
    depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075]
    order: 661
  - item: W62
    spec: VELDO-0077
    title: Objective acceptance and signed outcome assessment
    feature_refs: [F6]
    depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0076]
    order: 662
  - item: W63
    spec: VELDO-0078
    title: Backlog lifecycle and priority-controlled execution
    feature_refs: [F6]
    depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0076, VELDO-0077]
    order: 663
  - item: W64
    spec: VELDO-0079
    title: Grooming and admission requests through enrolled decision surfaces
    feature_refs: [F6]
    depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0078]
    order: 664
  - item: W65
    spec: VELDO-0080
    title: Section 2 work-class dispatch and trusted defect reproduction
    feature_refs: [F6]
    depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0079]
    order: 665
  - item: W66
    spec: VELDO-0081
    title: Quarantine inspection, taint propagation, and bounded execution
    feature_refs: [F6]
    depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0078]
    order: 666
  - item: W67
    spec: VELDO-0082
    title: Standing maintenance and compliance occurrence admission
    feature_refs: [F6]
    depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0079, VELDO-0081]
    order: 667
  - item: W68
    spec: VELDO-0083
    title: Bounded security emergency and incident containment admission
    feature_refs: [F6]
    depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0079, VELDO-0081]
    order: 668
  - item: W69
    spec: VELDO-0084
    title: Readmission, scope enforcement, and admission-debt reporting
    feature_refs: [F6]
    depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0079]
    order: 669
  - item: W70
    spec: VELDO-0085
    title: Decomposition and concurrent elaboration publication
    feature_refs: [F6]
    depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0078, VELDO-0079]
    order: 670
  - item: W71
    spec: VELDO-0086
    title: Release-execution ownership and contribution binding
    feature_refs: [F6]
    depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0076, VELDO-0077]
    order: 671
  - item: W72
    spec: VELDO-0087
    title: Project dependency invalidation and outcome-to-evidence traceability
    feature_refs: [F6]
    depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0084, VELDO-0085, VELDO-0086]
    order: 672
  - item: W73
    spec: VELDO-0088
    title: Project-manager execution graphs
    feature_refs: [F7]
    depends_on: [VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087]
    order: 773
  - item: W74
    spec: VELDO-0089
    title: Versioned team configuration
    feature_refs: [F7]
    depends_on: [VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087, VELDO-0088]
    order: 774
  - item: W75
    spec: VELDO-0090
    title: Capability-bound specialist selection
    feature_refs: [F7]
    depends_on: [VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087, VELDO-0089]
    order: 775
  - item: W76
    spec: VELDO-0091
    title: Budgeted requirements elaboration
    feature_refs: [F7]
    depends_on: [VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087, VELDO-0088, VELDO-0090]
    order: 776
  - item: W77
    spec: VELDO-0092
    title: Typed proposals and complete authorization validation
    feature_refs: [F7]
    depends_on: [VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087, VELDO-0088, VELDO-0089, VELDO-0091]
    order: 777
  - item: W78
    spec: VELDO-0093
    title: Per-project cycle serialization and replaceable checkpoint recovery
    feature_refs: [F7]
    depends_on: [VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087, VELDO-0088, VELDO-0089, VELDO-0090, VELDO-0091, VELDO-0092]
    order: 778
  - item: W79
    spec: VELDO-0094
    title: Every-pack runtime installation and floor-slice qualification
    feature_refs: [F8]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087, VELDO-0088, VELDO-0089, VELDO-0090, VELDO-0091, VELDO-0092, VELDO-0093]
    order: 879
  - item: W80
    spec: VELDO-0095
    title: Historical migration and atomic reader-writer cutover
    feature_refs: [F8]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087, VELDO-0088, VELDO-0089, VELDO-0090, VELDO-0091, VELDO-0092, VELDO-0093, VELDO-0094]
    order: 880
  - item: W81
    spec: VELDO-0096
    title: Clone and enrolled-principal adoption qualification
    feature_refs: [F8]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087, VELDO-0088, VELDO-0089, VELDO-0090, VELDO-0091, VELDO-0092, VELDO-0093, VELDO-0094, VELDO-0095]
    order: 881
  - item: W82
    spec: VELDO-0097
    title: Operational recovery under scope change, revocation, and lost effect acknowledgement
    feature_refs: [F8]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087, VELDO-0088, VELDO-0089, VELDO-0090, VELDO-0091, VELDO-0092, VELDO-0093, VELDO-0094, VELDO-0095, VELDO-0096]
    order: 882
  - item: W83
    spec: VELDO-0098
    title: Rollback compatibility and coordinated release qualification
    feature_refs: [F8]
    depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087, VELDO-0088, VELDO-0089, VELDO-0090, VELDO-0091, VELDO-0092, VELDO-0093, VELDO-0094, VELDO-0095, VELDO-0096, VELDO-0097]
    order: 883

regression:
  journeys:
    - id: RJ1
      title: R58 successful installed floor slice using fake model and real Git, files, SQLite, signing, locks, containment, gate, policy, and bare remote
      activation: {when: after:VELDO-0059}
      owner_spec: VELDO-0059
      profiles: [per_spec, release]
      suite: PLAN-0019 installed floor slice (planned; implementation must register executable checks)
    - id: RJ2
      title: R58 red gate and rejected approval leave local and remote trunk unchanged, including direct executor and review entry attacks
      activation: {when: after:VELDO-0059}
      owner_spec: VELDO-0059
      profiles: [per_spec, release]
      suite: PLAN-0019 floor failure isolation (planned; implementation must register executable checks)
    - id: RJ3
      title: R58 dependency or authority regression refuses execution and publication across direct entry points
      activation: {when: after:VELDO-0059}
      owner_spec: VELDO-0059
      profiles: [per_spec, release]
      suite: PLAN-0019 floor eligibility regression (planned; implementation must register executable checks)
    - id: RJ4
      title: R58 lost landing acknowledgement reconciles exact remote candidate without second publication
      activation: {when: after:VELDO-0059}
      owner_spec: VELDO-0059
      profiles: [per_spec, release]
      suite: PLAN-0019 landing recovery (planned; implementation must register executable checks)
    - id: RJ5
      title: R62 concurrent input, complete-read-set staleness, repeated graphs, missing specialists, escalation, and exhausted budgets refuse unsafe proposals
      activation: {when: after:VELDO-0093}
      owner_spec: VELDO-0093
      profiles: [per_spec, release]
      suite: PLAN-0019 project-manager concurrency and authority (planned; implementation must register executable checks)
    - id: RJ6
      title: R62 deterministic replacement adapter produces identical Veldo transitions for identical authorized proposals
      activation: {when: after:VELDO-0093}
      owner_spec: VELDO-0093
      profiles: [per_spec, release]
      suite: PLAN-0019 adapter equivalence (planned; implementation must register executable checks)
    - id: RJ7
      title: R62 checkpoint loss, disagreement, and deletion leave admission, dispatch history, decisions, and completion unchanged and repeat no committed effect
      activation: {when: after:VELDO-0093}
      owner_spec: VELDO-0093
      profiles: [per_spec, release]
      suite: PLAN-0019 checkpoint independence (planned; implementation must register executable checks)
    - id: RJ8
      title: R63 every composed pack installs its declared runtime and runs the first slice from the installed artifact
      activation: {when: after:VELDO-0098}
      owner_spec: VELDO-0098
      profiles: [per_spec, release]
      suite: PLAN-0019 every-pack installation (planned; implementation must register executable checks)
    - id: RJ9
      title: R63 another clone and fixture principal, restart, authority replacement, simulated machine loss, corruption, running revocation, and rollback compatibility
      activation: {when: after:VELDO-0098}
      owner_spec: VELDO-0098
      profiles: [per_spec, release]
      suite: PLAN-0019 operational adoption and recovery (planned; implementation must register executable checks)
    - id: RJ10
      title: R63 scope changes or authority is revoked during running work, then a crash follows an external effect before acknowledgement; conflicting observations on restart produce neither repeated effect nor unsupported completion
      activation: {when: after:VELDO-0097}
      owner_spec: VELDO-0097
      profiles: [per_spec, release]
      suite: PLAN-0019 decisive combined recovery (planned; implementation must register executable checks)

release:
  milestone: Dark Factory v1 - admitted projects reach proven outcomes through an installed recoverable authority
  mode: coordinated
  require_all_work_shipped: true
  require_full_regression: true
  rollback: >
    R27 preserves the previous known-good release and compatible schema reader until this release
    completes its proof plan. Corrupt authoritative history stops dispatch and is preserved for signed
    operations reconciliation against a verified replica. Rebuild derived tables only from verified
    history; checkpoint quarantine requires proof that domain history is intact. Never truncate an
    unexplained journal or implicitly downgrade a schema. Activation and rollback are receipted acts.
  observation:
    duration: Complete installed-pack and operational recovery qualification before activation; retain rollback material through the full proof plan.

open_decisions:
  - id: D1
    owner: Dmitry
    text: Dmitry must ratify SQLite as authority with a signed Git audit and recovery replica before effective policy and storage implementation.
    blocks: [VELDO-0016, VELDO-0023, VELDO-0024, VELDO-0044, VELDO-0048]
  - id: D2
    owner: Dmitry
    text: Dmitry must ratify off-host durable acknowledgement before mutation success, external dispatch, or dependent publication; local commit alone stays pending.
    blocks: [VELDO-0016, VELDO-0024, VELDO-0039]
  - id: D3
    owner: Dmitry
    text: Dmitry must ratify Linux systemd and cgroup v2 as the production runner requirement before lifecycle policy, containment, and service activation.
    blocks: [VELDO-0016, VELDO-0040, VELDO-0041, VELDO-0047]
  - id: D4
    owner: Dmitry
    text: Dmitry must ratify isolated per-run clones with a pinned read-only shared object cache before provisioning replaces shared worktrees.
    blocks: [VELDO-0016, VELDO-0042]
---

## Intent

**Purpose.** Veldo will carry a project owner's proposed objective through requirements, deliberate admission, bounded engineering, and accepted outcomes. The project manager may reason and propose; deterministic services alone authenticate, authorize, persist, schedule, and publish. Each implementing agent inherits this boundary even when its immediate item concerns only one schema or adapter. The full normative design is [the controlling R01-R76 document](../docs/design/PLAN-0019-dark-factory-design.md).

**Trust.** The existing specification, proof, review, gate, and serialized landing machinery is the factory floor and must be repaired before coordination depends on it. A successful process, model assertion, tracker status, graph checkpoint, or locally committed transaction does not establish accepted completion. Owners answer on enrolled input surfaces, with the exact presentation and canonical actor evidence bound to one settlement in Veldo. Projects, plans, releases, and behavior floors retain distinct meanings and authority.

**Delivery.** Build the contracts and durable control foundation first, prove a real installed floor slice with a fake model, then qualify production engines and decision channels. Only after those boundaries work may project operations and model coordination rely on them. These artifacts remain drafts; the four architectural recommendations await Dmitry, and no implementation, channel activation, or operational authority is claimed here.

## Ordered delivery rationale

**A before B.** Seven separate contracts define policy activation, entities, releases and floors, the combined graph, signing, completion, and admission. Identity and policy framing can begin independently. Completion depends on graph, release, and authority contracts; admission depends on identity and authority. B depends on all A contracts and supplies the durable store, recovery commands, real process containment, routing, accounting, and runtime packaging. VELDO-0015 is inspected existing behavior, with its three report repairs explicitly assigned to B.

**B before C.** Every C item depends on the completed A and B packages. C repairs floor consumers and connects real infrastructure from admission to remote-confirmed completion. The installed slice proves negative paths on the same direct executor and review entry points. Model output alone is faked. Its authorization fixtures cannot certify live decisions. Within each package, the listed order is the delivery frontier tie-breaker; package barriers are explicit dependencies, not an assertion that a partial package qualifies its successor.

**C forks to D and E.** Production-engine qualification and channel decision work may proceed independently after the floor slice. E owns every-channel presentation, canonical attribution, restricted edge keys, one atomic settlement, decision reviews, and tripwires. Per-channel sandbox proof gates live activation. F depends on E for project, objective, admission, grooming, quarantine, and dependency operations. G joins D and F before any model-mediated project-manager execution.

**H closes adoption.** H explicitly depends on every earlier package. Distribution starts in B and is exercised in C; H closes every-pack installation, migration, operational recovery, and rollback compatibility. The R58, R62, and R63 journeys require observed receipts over their full declared universes, not declarations alone. The coordinated milestone requires all work shipped and full regression. Packages A through E have draft specifications; F-H have allocated plan references only, and their specifications will be authored as their contracts become stable. Drafting B through E neither resolves D1-D4 nor activates their runtime boundaries.
