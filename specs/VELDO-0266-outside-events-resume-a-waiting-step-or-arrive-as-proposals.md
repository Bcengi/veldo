---
schema: veldo.spec/v1
id: VELDO-0266
title: A step waits for an outside callback through a signed, single-use, expiring resume link with a required timeout, and outside events from configured sources arrive as proposals in the owner's inbox, every one authenticated behind the outside gate, rate-limited, deduplicated and journaled, and nothing starts without the normal approvals
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0057, VELDO-0068, VELDO-0126, VELDO-0130, VELDO-0141, VELDO-0154, VELDO-0181, VELDO-0240, VELDO-0241, VELDO-0245, VELDO-0247, VELDO-0249, VELDO-0251, VELDO-0252, VELDO-0253, VELDO-0254, VELDO-0255, VELDO-0258, VELDO-0259, VELDO-0262, VELDO-0263]
placement: [contracts, engine, loop]
protected_paths: []
footprint:
  - ".veldo/control_workflow*.py"
  - "engine/.veldo/control_workflow*.py"
  - "packs/*/.veldo/control_workflow*.py"
  - ".veldo/control_graph_steps.py"
  - "engine/.veldo/control_graph_steps.py"
  - "packs/*/.veldo/control_graph_steps.py"
  - ".veldo/control_outside_events*.py"
  - "engine/.veldo/control_outside_events*.py"
  - ".veldo/outside_ingress*.py"
  - "engine/.veldo/outside_ingress*.py"
  - ".veldo/egress_gate.py"
  - "engine/.veldo/egress_gate.py"
  - ".veldo/gate_supervision.py"
  - "engine/.veldo/gate_supervision.py"
  - ".veldo/control_intake*.py"
  - "engine/.veldo/control_intake*.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_schedule*.py"
  - "engine/.veldo/control_schedule*.py"
  - ".veldo/control_store*.py"
  - "engine/.veldo/control_store*.py"
  - ".veldo/control_event_vocabulary.py"
  - "engine/.veldo/control_event_vocabulary.py"
  - ".veldo/installation.py"
  - "engine/.veldo/installation.py"
  - ".veldo/installation_schema/**"
  - "engine/.veldo/installation_schema/**"
  - ".veldo/installation_template/**"
  - "engine/.veldo/installation_template/**"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  - "docs/installation.md"
  - "scripts/suites/*_veldo_0266_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0266-outside-events-resume-a-waiting-step-or-arrive-as-proposals.md"
  - "specs/index.md"
  - "proof/VELDO-0266/**"
behavior_bearing: true
observability:
  logs: >
    Every inbound call is journaled once, accepted or refused: the receiving route (resume or a named
    source), the time, the peer address, the body's size and sha256, the source's event id when it has
    one, the verification result, the rate-limit and duplicate decisions, and the outcome (resumed
    unit and node, proposal id, or the refusal by name). Every resume link minted is journaled with the
    unit, node, attempt, revision digest and expiry, and the token only as its digest. A wait that times
    out is journaled with its bound. No signing secret, token, signature header or private field's value
    is ever logged; a payload field is logged only when it is declared and not marked private, otherwise
    as its digest.
  metrics: >
    Counted from the journal: inbound calls per route and source by outcome, refusals by name, duplicates,
    rate-limited calls, waits resumed and timed out per workflow and node, and the time from link minted
    to resume. VELDO-0265 reads them from the same events.
  traces: >
    A resume joins to its unit, cycle, node, attempt and revision {id, version, digest}, and to the
    journaled inbound call that carried it; a proposal from an outside event joins to that call and to
    the intake record of VELDO-0126, and the unit the owner later admits from it joins to the proposal.
  error_taxonomy: >
    Inbound refusals, each journaled with its name and answered to the caller with one uniform status and
    no detail: missing_authority:outside_signature, missing_authority:resume_unknown,
    stale_subject:resume_used, stale_subject:resume_expired, stale_subject:outside_timestamp,
    stale_subject:outside_duplicate, invalid_input:outside_payload, invalid_input:outside_too_large,
    unavailable_service:outside_rate_limited, unsupported_configuration:outside_source. New save problems:
    wait_timeout_required, wait_timeout_port_required, wait_fields_invalid, wait_link_target_invalid.
    New configuration refusals: installation_invalid:sources and invalid_input:source:literal_secret.
acceptance_criteria:
  - id: AC1
    text: >
      A wait_for_event step waits for an outside callback with a required timeout and holds nothing. Its
      config is exactly {timeout, fields, link_for}: timeout in seconds, required, within WAIT_CEILING
      (declared beside STEP_CEILING); fields the payload it accepts, declared like VELDO-0247's fields
      (type, size bound, private), and nothing else ever reaches the unit; link_for a node that lies on every path to the wait with no
      other wait between them, whose dispatch receives the resume link
      as data so it can hand it to the outside job (a callback URL, a commit status, a message). Its ports
      are `arrived` and `timed_out`, each with exactly one transition; a wait without a timeout or without
      a timed_out transition is refused at save, and the approval walk (VELDO-0241, VELDO-0247) follows
      both ports. The kind is marked changes_subject false, so it may sit after an owner_approval, and it
      is not outward. When a unit's link_for node is dispatched, the domain side asks the check service
      behind the outside gate (VELDO-0252) to mint the link: 256 random bits bound by the check service's
      own key to the unit, node, attempt, revision digest and expiry, and the wait's timeout runs from
      the moment the link is minted, so the link and the wait end together; the authority stores only the token's digest and the expiry. Waiting
      holds no worker, account or reservation; the timeout is a one-time occurrence of kind
      workflow_wait in VELDO-0240's schedule store, woken by the service loop's one timer (VELDO-0154),
      cancelled when the wait is resumed. Rows: a wait with no timeout, a wait with no timed_out
      transition, a field of an undeclared type and a link_for node not on every path are refused at save
      with the named problem; a unit reaching a wait holds no account and is listed waiting; with no call
      before the bound it takes timed_out once; a restart during the wait neither loses nor doubles the
      timeout.
    falsified_by: >
      Two registered mutations, each with a green baseline: (1) the save check accepts a wait with no
      timed_out transition: the timeout-port row goes red; (2) the authority stores the token itself
      rather than its digest: the token-at-rest row, which searches the store and the journal for the
      minted token's bytes, goes red.
  - id: AC2
    text: >
      A resume call is authenticated behind the outside gate, used once, before its expiry, and carries
      data only. Inbound calls reach Veldo only through an inbound listener of the outside gate (VELDO-0251,
      agentgateway), configured by egress_gate's generator from the installation, with a body size bound
      and per-route rate limits; the authority's own API (VELDO-0130) stays on loopback and gains no public
      route. The check service verifies the link's binding and expiry with its own key, and the authority
      then consumes the token by compare-and-set on its digest, so of two concurrent calls with the same
      link exactly one resumes and the other is refused stale_subject:resume_used. The payload is checked
      against the wait's declared fields (no field means no route, as VELDO-0247 rules) and only those
      values enter the unit as the wait node's named results, private ones stored as the field rules say.
      A resume moves the unit only from that wait node of that attempt of that revision: it cannot
      approve, admit, answer for the owner, choose a port, or skip a step, and every outward step after it
      still needs the owner's approval of that exact subject (VELDO-0057, VELDO-0068). Every refusal
      answers the caller with one uniform status and no detail, and is journaled with its name. Rows: a
      valid call resumes the unit through arrived with the declared fields; the same link again is
      refused resume_used; a link after its expiry, a link with one bit changed, a link bound to another
      node, and a link for a unit that already took timed_out are each refused by name and change nothing;
      a payload with an undeclared field or a value of the wrong type is refused outside_payload; a body
      over the bound is refused at the gate; two concurrent calls with one link resume once; a call that
      sets a field named approved, port or next changes no route.
    falsified_by: >
      Three registered mutations, each with a green baseline: (1) the authority reads the token without
      compare-and-set: the concurrent-calls row goes red with two resumes; (2) the expiry check is
      skipped: the expired-link row goes red; (3) undeclared payload fields are merged into the unit: the
      undeclared-field row goes red.
  - id: AC3
    text: >
      Outside events from configured sources arrive as proposals in the owner's inbox and never as work.
      A source is declared in the installation folder (VELDO-0259) under sources/<name>.yaml: a
      verification scheme from a closed set (HMAC-SHA256 over the timestamp, the event id and the body in
      the form of the Standard Webhooks specification; the same with an Ed25519 public key; and GitHub's
      X-Hub-Signature-256 HMAC form), a keystore reference for its secret resolved gate side (VELDO-0254,
      VELDO-0258), never a literal (invalid_input:source:literal_secret), a timestamp tolerance, a rate
      limit, a body bound, the event types it accepts, and a closed mapping from declared payload fields to
      the proposal's project, title and description. Adding or widening a source is a configuration
      change that goes live only after the owner approves that exact commit (VELDO-0253). The check
      service verifies the signature and timestamp with the source's secret, which never leaves it, and
      deduplicates by source and event id over a ledger kept at least as long as the timestamp tolerance,
      in the form of VELDO-0249's replay ledger; the authority deduplicates again through VELDO-0126's
      source request identity (the source name and event id), so the same event twice gives the same
      proposal and a changed body under the same id is refused as an identity conflict. A verified event
      enters the one normalized intake path of VELDO-0126 as a submission from that source and produces
      only an inbox proposal marked with its source and the inbound call's journal position; intake never
      admits or prioritizes it, and the owner admits it like any proposal. Its text is outside content:
      shown to the owner and to any later worker as data from that source, never as an instruction
      (VELDO-0181). Rows: a correctly signed event produces one proposal; a wrong signature, a timestamp
      outside the tolerance, an unknown source, an event type the source does not accept and a body over
      the bound are each refused by name and produce nothing; the same event resent gives the same
      proposal; a burst over the source's limit is refused rate_limited past the limit and journaled; no
      proposal is ever admitted without the owner's decision.
    falsified_by: >
      Three registered mutations, each with a green baseline: (1) signature verification accepts a
      timestamp outside the tolerance: the stale-timestamp row goes red; (2) the intake admits a verified
      event as an executable unit: VELDO-0126's never-admits falsifier and this suite's no-admit row go
      red; (3) the check service ledger is bypassed and the authority's identity check removed: the
      resend row goes red with two proposals.
  - id: AC4
    text: >
      Secrets stay behind the outside gate, and the authority's exposure does not grow. The check service
      alone holds the resume-link key and every source secret, resolved from the keystore gate side; the
      authority, the step runner and every worker run hold only token digests and verified, normalized
      payloads, and a gate row proves that no module in the authority's static closure, the runner or the
      launch path reads a source secret or the link key. The resume link itself is a bearer capability
      scoped to one wait: it is delivered only in the link_for node's dispatch, redacted from the
      execution record (VELDO-0141) to its digest after delivery, and caught by the secret scan
      (VELDO-0254) if it appears anywhere else. The inbound listener is supervised and health-checked with
      the gate (VELDO-0255); if it is down, callers are refused at the network and waits take timed_out at
      their bound, and nothing is queued outside the journal. With no source configured and no wait in any
      bound revision, the inbound listener is not started. Rows: the closure row is green; a planted copy
      of a source secret in the authority's environment is found by the closure row's runtime check and
      refused at start; a run's execution record shows the link only as its digest; with no sources and no
      waits, no inbound port is open.
    falsified_by: >
      Two registered mutations, each with a green baseline: (1) the authority verifies source signatures
      itself with the secret passed to it: the closure row goes red naming the module; (2) the execution
      record keeps the link in clear: the record-redaction row goes red.
required_evidence: [unit, integration]
rollback: >
  Revert the commits. wait_for_event is unregistered, so a stored revision that uses it no longer
  validates and a unit bound to it stops at its next station with missing_workflow and is put to the
  owner; outstanding links stop resolving because their digests are no longer read, and their timeout
  occurrences are ended. The inbound listener and its routes are removed from the gate configuration;
  sources in the installation folder are refused as installation_invalid:sources and the owner removes
  them by an approved commit. Proposals already in the inbox stay as proposals. Journal entries, ledgers
  and unit records stay as written. No automatic rollback, retry or recovery is authorized.
---

## Intent

Veldo can wait for a time and for the owner, but not for the world: a CI run on a remote the factory
pushed to, a deploy's health signal, a co-owner's review, a client's reply to a delivered document, a
vendor's slow job. Today such a step polls from inside a worker run, which burns an account, or the owner
tells the factory by hand. And the natural sources of work for a software factory are events (CI red on
trunk, a production alert, an issue opened by a user, a dependency advisory), which reach it only when the
owner retypes them. This adds a wait step resumed by a signed, single-use, expiring link with a required
timeout, and lets configured outside sources send events that arrive as proposals in the owner's inbox.
Every inbound call is authenticated behind the outside gate, rate-limited, deduplicated and journaled,
and nothing it carries can admit, approve or start work.

## Context

Owner, Telegram 39631 to 39633 (2026-11-07): the comparison of Veldo with n8n and its recommendation, and
"It's OK for work to coming in other ways". That relaxes the owner's ruling of 2026-09-22, Telegram 28857,
which limited new-work triggers to a Telegram message or an authenticated API call and dropped webhook
triggers (VELDO-0126 Notes and its out-of-review-scope line). Under the new word, outside events may start
work or resume a waiting step, still entering as proposals that pass Veldo's approvals. This spec covers
gaps 3 and 8 of research/veldo-n8n-gaps-2026-11-07.md in the owner's research folder.

What is there today. VELDO-0126 is the one normalized intake path: intake never admits or prioritizes
work, and a repeated source request identity gives the same proposal. VELDO-0130's API is loopback only
behind a TLS terminator, with single-use signed assertions for writes and no rate limiter. VELDO-0251 puts
every outside call of a run through one outside gate (agentgateway, Apache-2.0, pinned); VELDO-0252's check
service behind it holds credentials and verifies approval tokens; VELDO-0249 gives a single-use token with
a replay ledger; VELDO-0254 keeps credentials out of runs and scans for leaked ones; VELDO-0255 supervises
and health-checks the gate; VELDO-0258 and VELDO-0259 put Veldo's own settings in one installation folder
and its credentials in the keystore. VELDO-0240 and VELDO-0245 give one schedule store, woken by the
service loop's one timer (VELDO-0154).

Design decisions.
- Inbound calls end at the outside gate, not at the authority. The public surface is the gate's inbound
  listener; verification happens in the check service, which already holds secrets; the authority sees
  only verified, normalized commands, as it does for every other source. The authority's attack surface
  and its key material do not grow.
- Two layers of deduplication: the check service's ledger stops a replay at the edge, and VELDO-0126's
  source request identity keeps the proposal idempotent even if the ledger is lost or the event is
  resent after its window.
- Verification schemes are a closed list of published forms, not a library: Standard Webhooks
  (standardwebhooks.com, an open published specification) in its HMAC and Ed25519 variants, and
  GitHub's HMAC header form, which covers the common senders. A new scheme is a spec change.
- The resume link is minted before the outside job starts, through the link_for node, because the job
  needs the link to call back. It is a capability for one wait only, so it is treated like a secret in
  records and scans even though it grants no authority.
- A required timeout and a required timed_out port: no unit can wait forever on a world that never calls.
- Refusals are uniform to the caller and named in the journal, so the inbound route is no oracle for
  which links or sources exist.

Dependency on landing-b and VELDO-0262. VELDO-0241, VELDO-0247 and VELDO-0254 to VELDO-0259 as built are
in the landing-b batch, not on main at afa292f0; VELDO-0249, VELDO-0251 to VELDO-0253 are ready in their own
worktrees; VELDO-0240 and VELDO-0245 are ready and not yet built. This spec is built after all of them and
after VELDO-0262, against Veldo's own step runner, and uses VELDO-0263's failed port for a wait's
failures other than its timeout.

## Out of scope

Polling an outside service for events, and any watcher. Outside events that admit, prioritize or approve
anything. Inbound calls that carry files. Waiting on a form the factory serves (a later spec on this
step). A test URL that shows inbound data live on the canvas (gap 2 of the research, its own spec). A
public route on the authority's API. Mutual TLS or IP allowlists per source, which the gate may add later
as a configuration of the same listener. Canvas palette and inspector entries for wait_for_event and
sources, which belong to VELDO-0246 and read this spec's named problems.

## What the reviewer judges

- Normal use: a deploy workflow pushes a release and waits up to an hour for the CI callback, then goes
  on to its health check, or takes timed_out to ask the owner; a CI system sends "trunk red" and a
  monitoring tool sends a production alert, each appearing in the owner's inbox as a proposal with its
  source, which the owner admits or dismisses.
- Threat model: a forged or replayed callback; a link reused, guessed, shared to another unit or used
  after expiry; two racing calls; a payload that smuggles a route, an approval or an instruction; a flood
  from one source; a source secret or link key reaching the authority, a run or a log; an event that
  becomes executable work without the owner; an inbound listener that answers differently for valid and
  invalid links; a wait that never ends.
- The relaxation of Telegram 28857 is used exactly as the owner gave it: outside events may start work
  or resume a waiting step, and they enter as proposals or data, never as decisions.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962).

## History

2026-11-07: drafted under owner Telegram 39631 to 39633 (the n8n comparison and its recommendation, and
"It's OK for work to coming in other ways", which relaxes his ruling of 2026-09-22, Telegram 28857, that
only Telegram messages and API calls start work), from main at afa292f0, VELDO-0241, VELDO-0247 and
VELDO-0254 to VELDO-0259 as written in the landing-b batch, and VELDO-0262 as ready. Built after landing-b
lands and after VELDO-0262 and VELDO-0263. Standalone; no plan work item.
