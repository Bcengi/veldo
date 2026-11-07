---
schema: veldo.spec/v1
id: VELDO-0265
title: Run insights show per workflow, revision and step where time, failures, retries and model-account usage go, in the web UI and as an OpenTelemetry export of the journal, derived read-only from the journal with no new store of record
status: draft
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0051, VELDO-0062, VELDO-0130, VELDO-0131, VELDO-0141, VELDO-0154, VELDO-0166, VELDO-0229, VELDO-0241, VELDO-0246, VELDO-0247, VELDO-0253, VELDO-0254, VELDO-0258, VELDO-0259, VELDO-0262, VELDO-0263, VELDO-0264]
placement: [metrics, loop, contracts]
protected_paths: []
footprint:
  - ".veldo/control_insights*.py"
  - "engine/.veldo/control_insights*.py"
  - ".veldo/control_telemetry_export*.py"
  - "engine/.veldo/control_telemetry_export*.py"
  - ".veldo/control_event_projection.py"
  - "engine/.veldo/control_event_projection.py"
  - ".veldo/control_event_vocabulary.py"
  - "engine/.veldo/control_event_vocabulary.py"
  - ".veldo/control_api.py"
  - "engine/.veldo/control_api.py"
  - ".veldo/control_api_models*.py"
  - "engine/.veldo/control_api_models*.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_plane_calls.json"
  - "engine/.veldo/control_plane_calls.json"
  - ".veldo/installation.py"
  - "engine/.veldo/installation.py"
  - ".veldo/installation_schema/**"
  - "engine/.veldo/installation_schema/**"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  - "engine/ui/src/features/insights/**"
  - "engine/ui/src/features/workflow/**"
  - "engine/ui/src/views/InsightsView.vue"
  - "engine/ui/src/router/**"
  - "engine/ui/src/api/**"
  - "engine/ui/e2e/insights.spec.ts"
  - "engine/ui/e2e/fixtures.ts"
  - "docs/installation.md"
  - "scripts/suites/*_veldo_0265_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0265-run-insights-per-workflow-revision-and-step.md"
  - "specs/index.md"
  - "proof/VELDO-0265/**"
behavior_bearing: true
observability:
  logs: >
    The insights projection logs each advance of its watermark (from and to journal positions, events
    read, elapsed milliseconds) and each rebuild from zero with its reason. The exporter logs each
    batch it sends (destination name, first and last journal position, record and span counts, bytes,
    the destination's answer and elapsed milliseconds), each batch it holds back and why by name, and
    each change of its watermark. A refused configuration is logged with its key. No credential, no
    header value and no private field's value is ever logged.
  metrics: >
    The exporter's own lag (journal head minus its watermark, in events and seconds), batches sent and
    refused by reason, and the projection's lag, each computed from the journal and the watermarks and
    shown on the insights page beside what it measures.
  traces: >
    The export maps a unit to one trace, each cycle and child cycle to a span under it, and each step
    attempt to a span under its cycle, with ids derived from Veldo's own identities, so the same journal
    exports the same ids every time and a receiver can join a re-sent batch to what it already holds.
  error_taxonomy: >
    New names, each mapped onto control_service.CLASSES: insights_unavailable (unavailable_service, the
    projection is behind and the page says so with its lag), export_destination_refused
    (unavailable_service), export_redaction_refused (invalid_input, a batch held back because the
    secret scan or the attribute allowlist found something; nothing of it is sent),
    installation_invalid:telemetry and invalid_input:control_plane_credential for a bad export
    configuration, as VELDO-0258 and VELDO-0259 name them.
acceptance_criteria:
  - id: AC1
    text: >
      Insights are derived from the journal and the unit step records alone, and can always be rebuilt.
      control_insights is a projection in the form of VELDO-0051's: it reads the committed journal in
      order from a stored watermark and keeps its aggregates as a derived, discardable read model, never
      as a record any decision reads; deleting it and replaying the journal from zero gives byte
      identical aggregates in canonical JSON. Grouped by workflow id, version and digest, and within a
      revision by node (a child cycle's nodes under their call path, VELDO-0264, and each item under its
      each node), it computes: units started, finished and stopped; attempts, retries, timeouts and
      failures by named class (VELDO-0263); time per step split into running, waiting for a retry,
      waiting on the owner (approval and answer), waiting for an account or reservation, waiting for an
      outside event or a schedule, and queued for concurrency, each as count, median, p95 and total;
      and model-account usage per step from the usage records of VELDO-0062 and VELDO-0166, in the
      units the engine reported (invocations, messages, tokens or window share), by provider and
      account. Usage the record does not know is shown as unknown, never as zero, and no price is
      invented (VELDO-0131). The read model is advanced on the service loop's existing wake by journal
      commit (VELDO-0154), with no timer or poll of its own. Rows: on a recorded fixture journal covering
      success, retries, timeouts, an owner wait, a call, an each of three and an account-limited run,
      every aggregate equals a hand-computed expectation; a rebuild from zero equals the incremental
      result; a run with no usage observation shows unknown usage.
    falsified_by: >
      Two registered mutations, each with a green baseline: (1) the projection counts a retried attempt
      as a new unit: the retry-count row goes red; (2) unknown usage is summed as zero: the unknown-usage
      row goes red. A third check: the rebuild-equals-incremental row compares bytes, so any field the
      incremental path keeps outside the journal reds it.
  - id: AC2
    text: >
      The owner sees insights in the web UI on the house stack. A read route, reads.insights (GET
      /api/v1/domains/{domain}/insights, the owner's authenticated session, VELDO-0130), serves the read
      model for a chosen period, filtered by project, kind of work, workflow and revision, with the
      projection's lag. It writes nothing and carries no command. An Insights screen in engine/ui, built
      with Nuxt UI components (VELDO-0229) and the already pinned Chart.js and TanStack Table packages,
      adds no package to dependency-policy.json. It shows, per workflow and revision, units, failure
      rate, median and p95 duration, where the time went as one stacked bar per step (running, retry
      wait, owner wait, account wait, outside wait, queued), retries and timeouts by step, and usage by
      step and account; the owner can compare two revisions of one workflow side by side. The canvas run
      view (VELDO-0246 AC4) gains an insights overlay that shades each step of a revision by its share of
      time or of failures, read from the same route. Each number links to the units behind it. The page
      works at the widths VELDO-0246 tests (360, 390, 1280, 1440), in both themes, and passes the axe
      checks the UI suite already runs. Rows: the e2e fixture shows the expected numbers for two
      revisions; the overlay shades the slowest step darkest; a request without a session is refused
      unauthenticated; the dependency check passes with no new package.
    falsified_by: >
      Two registered mutations, each with a green baseline: (1) the screen sums owner wait into running
      time: the time-split row goes red; (2) the route serves the workflow head's nodes instead of the
      chosen revision's: the revision-compare row goes red.
  - id: AC3
    text: >
      The journal is exported as OpenTelemetry logs and traces, off by default. control_telemetry_export
      encodes OTLP over HTTP in its JSON form (the OpenTelemetry protocol specification, a CNCF project,
      Apache-2.0) with the Python standard library, so the engine gains no third-party import. Each
      journal event becomes one log record with its journal position, type, time and an allowlisted
      attribute set per event type; each unit becomes a trace, each cycle and child cycle a span, each
      step attempt a span with its revision, node, attempt number, outcome and failure class, and waits
      as span events. Trace and span ids are derived from the unit, cycle, node and attempt identities
      by digest, so a re-sent batch carries the same ids. The exporter is a second reader of the journal
      in the form of VELDO-0051's projector, with its own watermark advanced only after the destination
      accepts a batch; it sends at least once and in journal order, never skips a position, and backs
      off on a refusal by VELDO-0263's backoff rule without blocking the authority or the loop. It is
      configured in the installation folder (VELDO-0259) as a telemetry destination: endpoint, the
      signals sent, batch bounds, and a credential reference resolved from the keystore as a registered
      control-plane call (VELDO-0258, control_plane_calls.json). Turning it on or widening what it sends
      is a configuration change that goes live only after the owner approves that exact commit
      (VELDO-0253). Rows: with no telemetry configuration nothing is sent and nothing is opened; an
      OpenTelemetry Collector (CNCF, Apache-2.0) run in the integration suite as the receiver accepts
      every batch and its decoded traces hold the fixture's units, cycles and attempts with the expected
      parent links; a receiver that refuses twice then accepts gets every position exactly in order and
      the watermark never passes an unaccepted batch; a second export of the same journal yields the same
      trace and span ids.
    falsified_by: >
      Two registered mutations, each with a green baseline: (1) the watermark advances when a batch is
      sent rather than accepted: the refuse-then-accept row goes red with a missing position; (2) span ids
      are random: the same-ids row goes red.
  - id: AC4
    text: >
      Nothing private leaves in insights or the export, and both stay read-only. Every exported attribute
      comes from a closed allowlist per event type; a private field (VELDO-0247) is sent only as its
      digest; message text, worker output, file content, prompts and run records (VELDO-0141) are never
      sent, only their identities and sizes; every batch is redacted with the run's redaction set and
      then passed through the secret scan of VELDO-0254 before it is sent, and a batch with any finding
      is held back with export_redaction_refused, its positions named, and the owner told, never sent in
      part. No credential, header value or keystore reference appears in a metric, a log record, a span or
      the insights route. Neither the projection nor the exporter writes to the store, the journal or the
      installation repository, and no decision, dispatch or approval reads the insights read model; a
      gate row proves the static closure of every decision module imports neither. Rows: a fixture event
      whose private field holds a token-shaped value exports only its digest; a fixture whose allowlisted
      attribute carries a planted credential is held back by the secret scan and nothing of its batch
      reaches the receiver; a decision module that imports control_insights reds the closure row.
    falsified_by: >
      Two registered mutations, each with a green baseline: (1) the exporter skips the secret scan: the
      planted-credential row goes red because the receiver gets the batch; (2) a private field is sent in
      clear: the private-field row goes red.
required_evidence: [unit, integration, ui_states]
rollback: >
  Revert the commits. The insights route, screen, overlay and exporter go; the derived read model and the
  exporter's watermark are discarded, and nothing else read them. The journal, the store, unit records and
  usage records are untouched because neither part ever wrote them. A telemetry destination left in the
  installation folder is refused as installation_invalid:telemetry and the owner removes it by an
  approved commit. Data already sent to a destination stays there. No automatic rollback, retry or
  recovery is authorized.
---

## Intent

The spend view shows usage by account, project and run, but nothing answers the questions the owner
actually asks of the factory: which workflow fails most, where units spend their time (building, in
the gate, waiting on him, waiting for an account), how long approvals sit, how often a step retries,
and what a landed unit of each kind costs in account usage. Teams running Veldo on their own server
will also want its events in the monitoring they already run. This derives run insights per workflow,
revision and step from the journal, shows them in the web UI and on the canvas, and exports the journal
as OpenTelemetry logs and traces, read-only, with no new store of record.

## Context

Owner, Telegram 39631 to 39633 (2026-11-07): on the comparison of Veldo with n8n, asked for tickets for
step failure policy, sub-workflows and fan-out, and run insights first. This is the third; it is gap 6
of research/veldo-n8n-gaps-2026-11-07.md in the owner's research folder.

What is there today. VELDO-0051 gives one event vocabulary (control_event_vocabulary.py) and a projector
that publishes from the committed journal in order at a stored watermark (control_event_projection.py).
VELDO-0241 records each unit's step records against its pinned revision; VELDO-0263 and VELDO-0264 add
attempts, timeouts, child cycles and items. VELDO-0062 and VELDO-0166 record usage per account in the
units each engine reports, with no price. VELDO-0131's spend view uses Chart.js; VELDO-0229 moves the UI
onto Nuxt UI 4.12.0 with Chart.js 4.6.1 and TanStack Table 9.3.1 already pinned. VELDO-0154 wakes the
service loop on journal commits, run ends and account resets, with no other timer. VELDO-0258 registers
Veldo's own outside calls and takes their credentials from the keystore; VELDO-0259 gives one
installation folder and one reader.

Design decisions.
- One source of truth. Every number is computed from the journal and the records it points to. The read
  model is a cache with a watermark, rebuildable byte for byte, never read by a decision, so it cannot
  drift into a second record and cannot influence what the factory does.
- Incremental, not recomputed per request. The projection advances at journal commits, so the page costs
  the same whether the journal holds a thousand units or ten million; a rebuild from zero is the check
  that the increments are right.
- OTLP JSON over HTTP written with the standard library. The protocol is a stable published
  specification and the engine is standard library only; the OpenTelemetry Collector is used as the
  receiver in the proof, not shipped. Deterministic ids make delivery at least once safe to re-send.
- The export is a control-plane outside call of Veldo itself (VELDO-0258), not a run's call through the
  outside gate (VELDO-0251), and turning it on is the owner's approved configuration commit (VELDO-0253),
  because it sends the factory's activity to another system.
- Privacy by allowlist. Attributes are listed per event type, private fields go as digests, content is
  never sent, and the secret scan runs on every batch, so a new event field is not exported until
  someone lists it.

Dependency on landing-b, VELDO-0262, VELDO-0263 and VELDO-0264. VELDO-0241, VELDO-0247 and VELDO-0254 to
VELDO-0259 as built are in the landing-b batch, not on main at afa292f0; VELDO-0246 and VELDO-0253 are
ready in their own worktrees. The attempt, timeout, child cycle and item events this spec reads are
VELDO-0263's and VELDO-0264's; built after them, the projection covers them from the start. If it is built
first, those groupings are absent and are added by those specs, not guessed here.

## Out of scope

Metrics export (OpenTelemetry metrics, Prometheus); the numbers are on the page and derivable by any
receiver from the logs and traces. A "time saved" estimate per workflow. Alerting on insights. Exporting
run records' content, prompts or worker output. Any paid or hosted monitoring product. Retention or
deletion of the journal. Cost in money for subscription usage, which has no per-call price.

## What the reviewer judges

- Normal use: the owner opens Insights, sees that social posts wait on him a median of nine hours at the
  approval and that render retries twice in five units, compares the new revision of the document
  workflow with the old one, and clicks through to the slow units; a team sends the journal to the
  Collector it already runs and sees each unit as a trace.
- Threat model: a credential, a private field or content leaking through an attribute, a span name or an
  error detail; a watermark that skips a refused batch; random ids that duplicate on re-send; a read
  model that drifts from the journal or that a decision starts to read; export switched on without the
  owner's approved commit; a slow or hostile destination that blocks the loop.
- The page answers "where does the time go" truthfully: waits are separated from work, unknown usage is
  shown as unknown, and every number links to the units behind it.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962).

## History

2026-11-07: drafted under owner Telegram 39631 to 39633 (the n8n comparison and its recommendation:
tickets for step failure policy, sub-workflows and fan-out, and run insights first), from main at
afa292f0, VELDO-0241, VELDO-0247 and VELDO-0254 to VELDO-0259 as written in the landing-b batch, and
VELDO-0262 as ready. Built after landing-b lands, after VELDO-0262, VELDO-0263 and VELDO-0264.
Standalone; no plan work item.
