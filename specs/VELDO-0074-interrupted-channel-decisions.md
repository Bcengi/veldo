---
schema: veldo.spec/v1
id: VELDO-0074
title: Interrupted and concurrent decisions across enrolled channels
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W59
plan_revision: 1
depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0073]
placement: [tracker, engine, contracts, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request_reconcile.py"
  - ".veldo/request_reconcile.py"
  - "packs/*/.veldo/request_reconcile.py"
  - "engine/.veldo/request_projection.py"
  - ".veldo/request_projection.py"
  - "packs/*/.veldo/request_projection.py"
  - "engine/.veldo/request_doorbell.py"
  - ".veldo/request_doorbell.py"
  - "packs/*/.veldo/request_doorbell.py"
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/decision_review.py"
  - ".veldo/decision_review.py"
  - "packs/*/.veldo/decision_review.py"
  - "engine/.veldo/tripwire.py"
  - ".veldo/tripwire.py"
  - "packs/*/.veldo/tripwire.py"
  - "engine/.veldo/control_channel_journey*.py"
  - ".veldo/control_channel_journey*.py"
  - "packs/*/.veldo/control_channel_journey*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0074_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0074-interrupted-channel-decisions.md"
  - "specs/index.md"
  - "proof/VELDO-0074/*"
behavior_bearing: true
observability:
  logs: >
    Journey receipts identify channel pair, principal set, subject/presentation versions, fault
    barrier, restarted generation, winning settlement and retained losing evidence.
  metrics: >
    Report enrolled channel/pair coverage, crash-boundary coverage, terminal settlement counts,
    stale-answer refusals, and recovered projection effects.
  traces: >
    Join real platform presentation and answer evidence across authority death, subject change,
    restart, signed settlement, dependency updates, and terminal channel views.
  error_taxonomy: >
    Distinguish stale answer after restart, conflicting canonical history, duplicate principal
    quorum, revoked edge/member, partial settlement, and uncertain projection outcome.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: An interrupted decision whose governing subject changes refuses the pending stale
      answer after restart on every enrolled channel. Set: request_projection.project_requests,
      request_reconcile.reconcile_requests, authorization.is_authorized,
      decision_review.bind_review and tripwire.evaluate_readings in the installed decision path.
      Completeness: Derive the enrolled matrix from accepted W58 activation proofs; publish a real
      presentation in each sandbox, hold its answer pending, change the accepted subject or
      framing and then SIGKILL the authority. Restart with actual SQLite, signed Git replica and
      protected keys; deliver the original canonical answer. Require named stale refusal, reopened
      obligation and blocked dependent eligibility; a fresh current presentation and answer is the
      positive control. Falsifier: Recheck only bound subject ID after restart while ignoring its
      changed digest/presentation; journeys/interrupted-subject must detect stale settlement on an
      enrolled channel.
    falsified_by: >
      Recheck only bound subject ID after restart while ignoring its changed digest/presentation;
      journeys/interrupted-subject must detect stale settlement on an enrolled channel.
  - id: AC2
    text: >
      Claim: Concurrent answers within or across channels produce one valid terminal ruling with
      distinct-principal quorum and retained conflict evidence. Set: SettlementStore.settle
      through the enrolled W53 replacement, authorization._tally/is_authorized and
      request_reconcile._reconcile_one for all ordered channel pairs, including same-channel
      pairs. Completeness: Compare pair and race-order coverage to the enrolled registry. Use real
      sandbox messages or signed CLI commands, concurrent client processes, same and opposing
      rulings, stronger request roles, one principal on several channels, insufficient quorum,
      expired requests, and revoked membership/edge keys. Require one terminal version, no
      unauthorized rejection shortcut, and no channel-first precedence; capture winning and losing
      command results and full canonical history. Falsifier: Key terminal uniqueness by channel
      plus external message instead of request version; journeys/cross-channel-winner must detect
      two competing terminal settlements.
    falsified_by: >
      Key terminal uniqueness by channel plus external message instead of request version;
      journeys/cross-channel-winner must detect two competing terminal settlements.
  - id: AC3
    text: >
      Claim: Crashes around settlement and projection delivery preserve the committed outcome
      without repeated effects or fabricated certainty. Set:
      request_reconcile.FilesystemSettlementStore._apply replacement,
      request_projection._project_one, request_doorbell.ring and B signed journal/replica/cursor
      recovery used by every activated edge. Completeness: Enumerate actual transaction and
      external-effect barriers from installed instrumentation. SIGKILL before/during/after
      settlement commit, after replica acceptance before acknowledgment, after external
      creation/comment before response, and before cursor commit. Restart, remove graph
      checkpoints, and feed conflicting local observations; inspect all settlement tables,
      original nonces, canonical target history and receipt counts. Require old/new atomic state,
      pending exports, same correlation lookup, and AWAITING_AUTHORITY for unknown effects.
      Falsifier: Blindly repost a terminal projection after killing the edge just after external
      acceptance; journeys/projection-lost-ack must detect the repeated external effect.
    falsified_by: >
      Blindly repost a terminal projection after killing the edge just after external acceptance;
      journeys/projection-lost-ack must detect the repeated external effect.
required_evidence: [unit, integration, journeys]
rollback: >
  Withdraw qualification for affected channel configurations, stop new answer acceptance there,
  and retain all fault evidence and unresolved effects for original-identity recovery.
---

## Intent

Prove complete interrupted and concurrent decision journeys across the actual enrolled channel set.

## Context

Package E, W59 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A/B/C contracts govern implementation. This draft grants no implementation or activation authority.

R22-R23, R32-R33, R60, R71 and R72 require real journey evidence beyond C approval fixtures. Component success cannot establish stale-answer refusal after authority death or one winner across actual channels. The declared risk floor is critical; required approval must bind the eventual change and proof. This declaration records no approval.

## Out of scope

Provider engine certification, new channel protocols, and the H combined running-work/effect-loss journey are separate work.

## Notes

D1/D2 block real storage/replica recovery and D3/D4 remain inherited C prerequisites until Dmitry rules. Qualification requires the actual activated test-channel inventory, not an empty or hand-selected subset: declare supported enrollment configurations before ready, require each claimed channel and every ordered pair, and mark unavailable sandbox rows blocked. W58 supplies channel-specific activation; W59 never self-enables ingress. Only disposable test authorities, sandbox accounts and test targets are used. Preserve exact installed versions, process kill observations, canonical message identifiers and timestamps, signed source commands, and external effect counts. Map/inventory proposed control_channel_journey assets through W30. Each falsifier must change the real path, produce its named failing row and retained diff, then be reverted.
