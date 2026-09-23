---
schema: veldo.spec/v1
id: VELDO-0072
title: PLAN-0016 tracker projection and canonical-history repair
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W57
plan_revision: 1
depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0065, VELDO-0066, VELDO-0068]
placement: [tracker, contracts, distribution, docs]
protected_paths: []
footprint:
  - "engine/.veldo/request_projection.py"
  - ".veldo/request_projection.py"
  - "packs/*/.veldo/request_projection.py"
  - "engine/.veldo/request_reconcile.py"
  - ".veldo/request_reconcile.py"
  - "packs/*/.veldo/request_reconcile.py"
  - "engine/.veldo/tracker_adapter.py"
  - ".veldo/tracker_adapter.py"
  - "packs/*/.veldo/tracker_adapter.py"
  - "engine/.veldo/tracker_intake.py"
  - ".veldo/tracker_intake.py"
  - "packs/*/.veldo/tracker_intake.py"
  - "engine/.veldo/tracker_jira_live.py"
  - ".veldo/tracker_jira_live.py"
  - "packs/*/.veldo/tracker_jira_live.py"
  - "engine/.veldo/tracker_mirror.py"
  - ".veldo/tracker_mirror.py"
  - "packs/*/.veldo/tracker_mirror.py"
  - "engine/.veldo/tracker_mirror_runner.py"
  - ".veldo/tracker_mirror_runner.py"
  - "packs/*/.veldo/tracker_mirror_runner.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "plans/PLAN-0016-human-decisions-through-jira.md"
  - "scripts/suites/*_veldo_0072_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0072-tracker-projection-history-repair.md"
  - "specs/index.md"
  - "proof/VELDO-0072/*"
behavior_bearing: true
observability:
  logs: >
    Tracker repair receipts identify request/version, presentation digest, stable issue/comment
    correlation, fetched history range, and terminal projection source receipt.
  metrics: >
    Count revised briefs actually published, recovered comment acknowledgments, history gaps,
    duplicate correlations, and terminal mirror retries.
  traces: >
    Join PLAN-0016 issue correlation through canonical Jira pages and normalized account/time
    fields to shared settlement and its outbound terminal projection.
  error_taxonomy: >
    Distinguish stale permanent brief key, ambiguous marker, missing live adapter method,
    incomplete changelog, terminal-write fence refusal, and outcome unknown.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A changed brief is published under a version-and-content key and visibly supersedes
      the previous presentation without duplicating an unchanged retry. Set:
      request_projection._project_one/build_brief,
      tracker_adapter.TrackerAdapter.comment/FakeTracker._comment, and
      tracker_intake.JiraCloudAdapter._comment on the repaired PLAN-0016 path. Completeness:
      Publish two actual rendered revisions with the same request ID, changed choices or risk
      text, and then replay both. Compare external comment bytes and W50 presentation receipts,
      not only return counts. Kill after remote comment acceptance before acknowledgment; query
      the original correlation and digest rather than blindly repost. Run against a real Jira
      sandbox before live activation, with unsupported outcome lookup leaving explicit
      uncertainty. Falsifier: Restore the permanent request-ID brief key in _project_one;
      tracker/revised-brief-key must detect the revised comment suppressed by keyed deduplication.
    falsified_by: >
      Restore the permanent request-ID brief key in _project_one; tracker/revised-brief-key must
      detect the revised comment suppressed by keyed deduplication.
  - id: AC2
    text: >
      Claim: The live tracker adapter supplies complete canonical attributed history and durable
      unambiguous object correlation to existing reconciliation. Set:
      tracker_adapter.normalize_changelog/TrackerAdapter.read_changelog/find_child,
      tracker_jira_live.fetch_changelog,
      tracker_intake.JiraCloudAdapter._find_by_marker/_upsert_issue, and
      request_reconcile._opening_actor/_entry_actors/_settlement_record/reconcile_from_repo.
      Completeness: Exercise actual live adapter methods in a Jira sandbox, including multiple
      pages, duplicate markers, lost create acknowledgment, changed display name, unknown actor
      kind, and missing opening history. Inspect account_id/actor_kind/at end to end, use W51
      principal mapping, and refuse incomplete history or ambiguous search instead of choosing the
      first issue. Compare query coverage and stored correlations to every PLAN-0016 request
      touchpoint. Falsifier: Have _settlement_record read ts while canonical history supplies at;
      tracker/canonical-time must detect a settlement missing the platform timestamp.
    falsified_by: >
      Have _settlement_record read ts while canonical history supplies at; tracker/canonical-time
      must detect a settlement missing the platform timestamp.
  - id: AC3
    text: >
      Claim: Outbound tracker status and artifact views follow published authority receipts
      without becoming new decision evidence or bypassing the fenced runtime writer. Set:
      tracker_mirror.mirror_events/mirror_plan_events/_epic_veldo_status,
      request_projection.project_requests, and tracker_mirror_runner.reconcile/run_from_repo with
      the shared W53 settlement producer. Completeness: Replay real signed settlement/publication
      history through each request touchpoint and mirrored plan/spec outcome. Kill before and
      after external transition acknowledgment, restart, and compare stored cursors, issue
      history, and authority state. Ignore automation-originated terminal projections as fresh
      answers; a forbidden transition stays pending with a named fence refusal, never using an
      approver credential or altering the fence. A verdict or shipped string alone cannot supply
      terminal authority. Falsifier: Feed a runtime writer terminal projection back into
      reconciliation as a fresh approving actor; tracker/mirror-feedback must detect the second or
      unauthorized settlement.
    falsified_by: >
      Feed a runtime writer terminal projection back into reconciliation as a fresh approving
      actor; tracker/mirror-feedback must detect the second or unauthorized settlement.
  - id: AC4
    text: >
      Claim: PLAN-0016 remains the repaired compatibility path and its operating guidance reflects
      the later every-channel ruling and separate activation conditions. Set:
      request_reconcile.reconcile_from_repo, request_projection.project_from_repo,
      tracker_mirror_runner.build_live_adapter and
      plans/PLAN-0016-human-decisions-through-jira.md, with enrolled channel routing.
      Completeness: Inventory the actual PLAN-0016 entry points and deferred live methods against
      installed pack copies. Execute session-start canonical pull with real storage, require
      shared presentation/attribution/settlement guards, and test an independently enrolled
      chat/CLI channel with Jira disabled. Update stale tracker-only/no-chat guidance while
      retaining sandbox activation, two-key and no-bypass obligations; unavailable tracker ingress
      is visibly session-start only. Falsifier: Route the PLAN-0016 session-start pull through its
      legacy filesystem settlement writer after enrollment; tracker/compatibility-authority must
      detect a settlement outside the authority transaction.
    falsified_by: >
      Route the PLAN-0016 session-start pull through its legacy filesystem settlement writer after
      enrollment; tracker/compatibility-authority must detect a settlement outside the authority
      transaction.
required_evidence: [unit, integration]
rollback: >
  Pause tracker effects, preserve issue/comment correlations and pending receipts, and retain
  session-start read visibility while repairing the qualified adapter.
---

## Intent

Repair PLAN-0016 projection and canonical-history integration so Jira participates in the same authority as every other enrolled decision surface.

## Context

Package E, W57 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A/B/C contracts govern implementation. This draft grants no implementation or activation authority.

R28, R38, R41, R51, R60 and R72 require repair of the shipped path. The permanent brief key suppresses updates in the fake, while the live comment adapter posts without lookup; the live history and actor fields also need end-to-end consumption. The declared risk floor is high; required approval must bind the eventual change and proof. This declaration records no approval.

## Out of scope

New board workflows, live ingress enabling, general project intake, and replacement of the approval/two-key safety core are excluded.

## Notes

D1/D2 block accepted projection and settlement history; D3/D4 remain inherited C prerequisites. AC1 owns the reproduced projection comment key defect. Reuse W50 receipts, W51 attribution, and W53 settlement rather than implementing tracker-specific authority. Verify the actual PLAN-0016 filename before ready and retain original decisions as historical provenance while amending superseded instructions. All listed tracker/reconcile modules missing from engine require canonical copies, explicit W30 inventory and byte-identical pack coverage, not repository-only tests. Any workflow or policy mutation requires W58 activation qualification and its scoped approval; this footprint grants no board administration. Save canonical pages, rendered revised bytes, applied mutation diffs and named failures in secret-safe evidence.

## Revision 3 disposition

2026-09-22, owner Telegram 28857 and 28859: this Jira-specific factory channel work is
dropped. W57 remains in PLAN-0019's Release 4 allocation solely to preserve the existing work
identity and historical draft; it is not scheduled implementation, an activation prerequisite
or a promise to build Jira intake later. New work arrives only through Telegram or the
authenticated API. Agents may fetch referenced tickets using exactly their configured tools.
The historical criteria above are not a Release 1 test universe. Status remains unchanged.
