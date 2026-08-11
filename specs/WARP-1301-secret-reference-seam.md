---
schema: veldo.spec/v1
id: WARP-1301
title: A secret is named in the repository and resolved at the moment of use, and the agent-facing API
  structurally cannot return a value
status: shipped
risk: standard - a new module that resolves nothing on its own and ships only a fake store. It is not
  low because it is the seam every future secret flows through, and a design error here would put
  credentials within reach of an agent by construction rather than by accident.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0013
work: W1
depends_on: []
placement: [contracts]
footprint:
  - ".veldo/secretref.py"
  - "engine/.veldo/secretref.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/01_warp_0101_reviewer_notes.py"
  - "specs/WARP-1301-secret-reference-seam.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      THE AGENT-FACING CALL CANNOT RETURN A SECRET, and that is the whole design. `wire()` takes a
      reference and returns THE REFERENCE; it validates and never resolves. Telling an agent not to
      write literal credentials is a rule that holds until the model is tired or the context is long.
      Not having a function that returns a value into its reach is a property. A selftest asserts
      `wire` returns its input and that no agent-facing function resolves anything.
  - id: AC2
    text: >
      RESOLUTION RETURNS AN OPAQUE HANDLE, NEVER A BARE STRING, so a value cannot be picked up by
      accident from a return position. `SecretHandle.__repr__` and `__str__` both render the
      REFERENCE, because the commonest route a credential takes into a log is an exception formatter
      or a debug print rendering an object that happens to hold one, and neither calls `.reveal()`.
      A selftest asserts the secret appears in neither rendering.
  - id: AC3
    text: >
      FAIL CLOSED ON EVERYTHING UNRESOLVABLE, each by its own name: a malformed reference, an unknown
      scheme, and a name the store does not hold. AN ABSENT SECRET IS NOT AN EMPTY ONE - a resolver
      returning None or "" refuses, because an empty credential is accepted by some APIs and then
      debugged for a day. Errors carry the reference and never the value, since an error message is a
      log line waiting to happen.
  - id: AC4
    text: >
      ONE PARSER. `parse` is the only place the reference syntax is known; `is_reference`, `wire` and
      `resolve_for_runtime` all go through it, so a syntax change has exactly one site. The scheme
      vocabulary is declared once and an unknown scheme refuses rather than being guessed at, so a
      typo is a refusal and not a silent lookup miss.
  - id: AC5
    text: >
      PROVEN AGAINST A FAKE STORE, WITH NO REAL RESOLVER SHIPPED. Environment and keychain adapters
      are the blessed defaults per D1 but resolution is behind the seam; this module reaches nothing.
      A selftest asserts it imports nothing that could read a real credential store.
required_evidence: [unit]
rollback: >
  Delete the module and its capability entry. Nothing reads it yet, no gate stage runs it, it holds
  no state and resolves nothing.
---

## Outcome

A secret is NAMED in the repository and RESOLVED at the moment of use. The name is data an agent may
read, write and commit. The value is something an agent never sees.

## Why the split has to be structural rather than instructed

Ask an agent to wire up an API token and its default behaviour - learned from every codebase ever
written - is to put the literal string in a config file and move on. A rule saying not to holds
until the model is tired, the context is long, or the phrasing is unusual.

What holds instead is not having a function that returns a value into the agent's reach. `wire()`
hands back the reference it was given. There is no agent-facing path to a secret, so there is
nothing to resist.

## The handle, and the log line that never happens

Resolution returns a `SecretHandle`, not a string, so a value cannot be picked up by accident from
a return position. Both its renderings show the reference.

That is aimed at a specific, extremely common failure: a credential reaches a log because an
exception formatter or a debug print rendered an object holding one. Neither of those calls
`.reveal()`. Naming the accessor that way also means every deliberate use greps out in one search,
which is what makes auditing who touches secrets tractable at all.

## Absent is not empty

A store returning None or an empty string refuses. An empty credential is silently accepted by some
APIs and then debugged for a day, and "the secret was not there" is a far better failure than
"authentication mysteriously does nothing".
