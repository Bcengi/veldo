---
schema: veldo.spec/v1
id: VELDO-0000
title: <short title>
status: draft
risk: standard
owner: <the human accountable for the intent>
human_approval: not_required
lane: "standalone         # standalone (bug/isolated) | planned (bound to a Product Plan)"
protected_paths: []
# behavior_bearing (PLAN-0012 W9). Whether this change carries product behavior. When true,
# the spec declares observability criteria (logs, metrics, traces, error_taxonomy) and EVERY
# acceptance criterion below declares its own falsified_by.
# behavior_bearing: true
acceptance_criteria:
  - id: AC1
    text: <observable, testable requirement>
    # falsified_by is THE NEGATIVE CONTROL, declared in the criterion itself: the single
    # change to the implementation that must make this criterion's check fail. Required on
    # every criterion of a behavior_bearing spec, one statement, no exemption keyword. A
    # criterion that names no way to be proven wrong leaves the implementer to invent the
    # falsification, and the cheapest invention is one that passes.
    falsified_by: <the one change to the implementation that must turn this criterion red>
required_evidence: [unit]
rollback: <how this change is reverted or disabled>
---

## Intent

What outcome should become true, and why it matters.

## Context

Relevant background: product, technical, operational.

## Out of scope

What this change must not touch.

## What the reviewer judges

The scope an independent review holds this change to (owner ruling, Telegram 28961, 2026-09-23).
Three parts, each stated for THIS change:

- Normal use: who calls it, with what inputs, in what state of the repository and host.
- Threat model: who this change defends against, and who it does not. The default is the same
  account: code or files already running or planted as the owner are not an attacker this change
  defends against unless the change says otherwise.
- Out of review scope: the classes of finding that are filed as a later-release ticket instead of
  blocking landing: edge cases that are unlikely in normal use (owner, Telegram 28962: "We don't
  won't to overbuild now for edge cases that are highly unlikely or even just unlikely"), planted
  files in the installed directory, deliberately forged records in our own store, and resource
  exhaustion by our own account.

A finding inside this section is fixed before landing. A finding outside it is filed as a ticket
and does not block landing. A real defect under normal use is always inside it.

## Notes

Anything the implementing or reviewing agent needs.
