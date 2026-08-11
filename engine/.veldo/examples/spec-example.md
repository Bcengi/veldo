---
schema: veldo.spec/v1
id: WARP-0001
title: Payment retry idempotency
status: shipped
risk: high
owner: jane
human_approval: required
protected_paths:
  - billing/
acceptance_criteria:
  - id: AC1
    text: Retrying a failed payment with the same idempotency key never creates a second order.
  - id: AC2
    text: A duplicate submission returns the original order id in the standard response shape.
required_evidence: [unit, integration]
rollback: disable the payment_retry_v2 flag
---

## Intent

Customers must be able to retry a failed payment without creating a
duplicate order.

## Context

Example specification demonstrating the veldo.spec/v1 shape.

## Out of scope

Retry UI copy and cadence.
