---
schema: veldo.spec/v1
id: VELDO-0138
title: The authority service runs the Telegram ingress and takes the owner's activation commands
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0047, VELDO-0073]
placement: [engine, tracker, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_service*.py"
  - ".veldo/control_service*.py"
  - "packs/*/.veldo/control_service*.py"
  - "engine/.veldo/control_channel_ingress*.py"
  - ".veldo/control_channel_ingress*.py"
  - "packs/*/.veldo/control_channel_ingress*.py"
  - "engine/.veldo/control_channel_activation*.py"
  - ".veldo/control_channel_activation*.py"
  - "packs/*/.veldo/control_channel_activation*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "bin/veldo"
  - "engine/bin/veldo"
  - "scripts/suites/*_veldo_0138_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0138-authority-service-runs-telegram-ingress.md"
  - "specs/index.md"
  - "proof/VELDO-0138/*"
behavior_bearing: true
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The installed authority service, started through its ordinary VELDO-0047 lifecycle,
      runs the Telegram ingress that VELDO-0073's open_ingress builds from host configuration, so an
      enrolled owner's answer to a presented request settles through the running service. Set and
      completeness: Install the service with the scaffold, start it as the lifecycle does, present a
      request, deliver the owner's reply through a loopback Bot API stand-in, and read the settlement
      from the store in another process; with no activation record the service still starts and the
      ingress stays inert (not_activated, nothing sent or acquired). Falsifier: Start the service
      without calling open_ingress; the served-settlement row must fail.
    falsified_by: >
      Start the service without calling open_ingress; the served-settlement row must fail.
  - id: AC2
    text: >
      Claim: The owner qualifies, activates and stops the Telegram edge with his own signed
      command through bin/veldo, and the running service applies it; no other principal can.
      Set and completeness: Drive veldo channel qualify, activate and stop against the running
      service, signed by the owner's enrolled key; then the same commands signed by another member,
      by an agent_run or service principal, and unsigned; each refused by name with the activation
      record unchanged. A stop takes effect in the running service without a restart and keeps
      pending requests pending. Falsifier: Accept an activation command signed by a member who is
      not the owner; the owner-only row must fail.
    falsified_by: >
      Accept an activation command signed by a member who is not the owner; the owner-only row
      must fail.
  - id: AC3
    text: >
      Claim: A restart of the service keeps the edge exactly as the owner left it. Set and
      completeness: Restart the running service with the edge active, stopped and never activated;
      read acquisition, sends and pending requests after each. Falsifier: Start the ingress active
      after a restart that followed the owner's stop; the stopped-stays-stopped row must fail.
    falsified_by: >
      Start the ingress active after a restart that followed the owner's stop; the
      stopped-stays-stopped row must fail.
required_evidence: [unit, integration]
rollback: >
  Stop the edge with the owner's command and revert the service wiring; accepted evidence,
  activation records and pending requests are preserved.
---

## Intent

VELDO-0073 built the activation gate and the Telegram ingress, but nothing in the running factory
starts that ingress or accepts the owner's activation commands, so a real Telegram answer has no
production path to a settlement. This wires both into the authority service.

## Context

Found by VELDO-0073's first critical review (2026-09-24, filed item F1): control_service.py loads
none of the channel modules and channel_activation_authorize is registered only when something calls
open_ingress. No specification owned this. Qualification from VELDO-0073's live run is in a scratch
authority, so the real factory runs its own qualify, send and reply cycle with the owner's enrolled
key once this lands.

## Out of scope

Restart recovery of an interrupted exchange, retention, reconnect and reordering (Release 2); other
channels (Release 4); the authenticated API's own activation route (VELDO-0130).

## What the reviewer judges

- Normal use: the owner installs and starts the authority service as VELDO-0047 does; it runs the
  Telegram ingress from host configuration, inert until activated. The owner qualifies, activates and
  stops the edge with veldo channel commands signed by his enrolled key; the running service applies
  each without a restart. His answers to presented requests settle through the running service. A
  restart keeps the edge as he left it.
- Threat model: the ingress running or sending without an activation record; an activation, stop or
  qualification accepted from anyone but the owner, or unsigned; a stop that needs a restart to take
  effect or that drops pending requests; a restart that re-activates a stopped edge. The owner's
  account, the store, the installed engine and the Telegram edge are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); the Release 2
  items above; forged rows in our own store and files planted in the installed directory; the
  same-account class filed by VELDO-0040, VELDO-0058 and VELDO-0067.

## Notes

Reuse VELDO-0073's open_ingress and Activations unchanged where possible; the service owns their
lifetime. bin/veldo stays a thin dispatcher: veldo channel routes to the activation module's own
command surface.

The running factory's real-platform qualification happens here, live, once, with the owner: through
the running service, one decision is sent to his chat, he replies, and his enrolled key signs the
activation over the qualification the gate recorded in the factory's own store. That is the binding
proof VELDO-0073's committed live record cannot be (its second review showed a file cannot prove where
it came from).

## History

2026-09-24: written by the lead from VELDO-0073's first critical review (filed F1). Draft; the owner
decides readiness.

2026-09-24: the owner marked this specification ready on Telegram (29090 asked, 29091 "Yes").

2026-09-25: Notes name the live real-factory qualification as this item's, after VELDO-0073's second
review withdrew the claim that a committed record proves real-platform provenance.
