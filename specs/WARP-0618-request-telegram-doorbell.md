---
schema: veldo.spec/v1
id: WARP-0618
title: the request Telegram doorbell - a concise notice + link on a new or updated human touchpoint, a
  SIGNAL only that never captures a decision, idempotent per (request_id, status), send injected (W4 of
  the human-decision surface)
status: shipped
risk: standard - a small repo-only module that turns a veldo.request/v1 into a short notice string + a
  ticket link; the SEND is an injected/reference-wired seam that is NEVER run in the gate (a fake sink is
  what runs there), so it makes no network call in the gate and fails safe (a doorbell failure never
  blocks or advances a request). It touches NO protected path and nothing in the safety core, reads the
  request record read-only, and writes nothing back. A notice that would carry a secret/operating datum
  is redacted before it is emitted (reuses the W3 redactor), so the doorbell cannot leak to Telegram
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0016
work: W4
plan_revision: 1
placement: [tracker]
footprint:
  - .veldo/request_doorbell.py
  - .veldo/capabilities.yaml
  - engine/.veldo/capabilities.yaml
  - packs/*/.veldo/capabilities.yaml
  - .veldo/architecture.yaml
  - scripts/selftest.py
  - specs/WARP-0618-request-telegram-doorbell.md
  - specs/index.md
  - proof/WARP-0618/**
protected_paths: []
behavior_bearing: true
observability:
  logs: the doorbell reports each notice it would send (request id, status, the link) and whether it was
    suppressed as a duplicate, so a stranger sees what fired from the report alone.
  error_taxonomy: a send failure is caught and reported, never raised into the caller (fail-safe - a
    doorbell that cannot deliver must not block or advance a request); a request with no tracker link yet
    is skipped (nothing to link to), not errored; a notice is redacted before emit and a redaction miss
    fails closed (the field is dropped).
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Append an approve call to action (a "Reply YES to approve" line) to the body build_notice
      assembles at .veldo/request_doorbell.py:120-131, changing nothing else: the load-bearing leg
      here is SIGNAL ONLY, and the assertion that no delivered notice carries an approve or
      reply-with-a-decision call to action must go red.
    text: A pure function in a new repo-only module .veldo/request_doorbell.py turns a veldo.request/v1 into
      a concise notice (title + tier + a one-line what + the Jira ticket link from request.tracker) - a
      SIGNAL only. The notice NEVER carries an approve/decide action and the module has no path that reads
      a reply as a decision (Telegram is a doorbell; the decision lives in Jira). It reads the request
      read-only and writes nothing back.
  - id: AC2
    falsified_by: >
      Narrow the handler in ring from `except Exception as exc` to `except KeyboardInterrupt as exc`
      at .veldo/request_doorbell.py:153 so a FailingSink delivery error escapes into the caller, and
      the fail-safe assertion must go red, ring raising RuntimeError instead of returning outcome
      "failed" with the request byte-unchanged.
    text: The SEND is an INJECTED seam (a sink passed in), reference-wired like the live tracker adapter -
      the gate drives a deterministic fake sink with no network, and the real Telegram send is never run
      in the gate. A send failure is caught and reported, NEVER raised into the caller: a doorbell that
      cannot deliver must not block or advance a request (fail-safe).
  - id: AC3
    falsified_by: >
      Replace the closing `return redact(body, terms), link` of build_notice with `return body, link`
      at .veldo/request_doorbell.py:131. The load-bearing leg is the REDACTION rather than the
      idempotence, because a duplicate notice is spam while a leaked one is a disclosure, and the
      assertion that a notice built over a record carrying env:PROD_DB_PASSWORD and a declared
      operating term emits neither in the clear must go red.
    text: It is IDEMPOTENT per (request_id, status) - the same request at the same status notifies at most
      once, so a re-run or a re-projection does not spam; a genuine status change notifies again. The
      notice text is REDACTED before emit (reuses the W3 redactor / the same declared-scope + fail-closed
      discipline) so no secret reference or declared operating datum reaches Telegram.
  - id: AC4
    falsified_by: >
      Pass `_rd_src` unmutated into `_rd_mut` at scripts/suites/10_warp_0613_anti_vacuity.py:1028 so
      the T1 mutant keys its send exactly as the shipped module does, and T1's assertion that the
      mutant delivers twice while the real path delivers once must go red: a tooth that cannot
      separate the mutant from the shipped module is the vacuity this criterion exists to refuse.
    text: A selftest drives the doorbell over the deterministic fake sink offline (no network) and is
      NON-TAUTOLOGICAL - a new request notifies once with the correct title/tier/link; the same request at
      the same status does NOT notify again (idempotent); a status change DOES notify; a send failure is
      swallowed and the request is untouched (fail-safe); a notice carrying a secret/operating datum is
      redacted - each with an in-memory source-mutation TOOTH that turns its assertion red while the
      on-disk module stays byte-unchanged (neutralizing the idempotency key double-notifies; neutralizing
      the fail-safe wrap lets a send error escape; neutralizing the redactor emits the secret). None
      vacuous.
required_evidence: [unit]
rollback: git revert; additive - a new repo-only module, one capability entry (all eight capabilities.yaml
  byte-identical), the module declared in the tracker area of architecture.yaml, a selftest block, and
  this spec; no protected path; the send is an injected reference seam never run in the gate; pure stdlib.
---

## Intent

When a human touchpoint opens or changes, the responsible person gets a short nudge on Telegram with a
link to the Jira ticket - a doorbell, not the decision surface. The decision is always made and recorded
in Jira; Telegram only says "there is something for you, here is the link." This builds that: a pure
notice-builder + an injected send seam, idempotent so it does not spam, redacted so it cannot leak, and
fail-safe so a delivery problem never blocks or advances a request.

## Context

W4 of the approved human-decision surface (VEL-1), composing on W2 (veldo.request/v1, WARP-0615) as the
trigger and W3 (WARP-0617) for the ticket link + the redactor it reuses. It reads the request; it never
writes a record or reads a reply as a decision. The real Telegram send is reference-wired exactly like the
live tracker adapter and is never exercised in the gate.
