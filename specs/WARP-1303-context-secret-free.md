---
schema: veldo.spec/v1
id: WARP-1303
title: A context that never held a secret cannot leak one - redaction at the seam where data becomes
  context, not filtering of the transcript afterwards
status: shipped
risk: standard - a pure text seam that resolves nothing and holds only values its caller already had.
  It is not low because a redaction bug returns something that LOOKS scrubbed, which is worse than
  returning nothing, and because once a credential is in a context there is no recall.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0013
work: W3
depends_on: [WARP-1301]
placement: [contracts]
footprint:
  - ".veldo/context_redaction.py"
  - "engine/.veldo/context_redaction.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/01_warp_0101_reviewer_notes.py"
  - "specs/WARP-1303-context-secret-free.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      A SEEDED SECRET IN SOURCE DATA NEVER APPEARS IN THE CONTEXT, which is this item's conformance
      requirement stated directly. A selftest puts a known credential into a log-shaped blob, admits
      it through the seam, and asserts the value is absent from the result.
  - id: AC2
    text: >
      KNOWN VALUES ARE REDACTED BY VALUE, NOT BY SHAPE, and that is the part that actually protects.
      Anything the runtime resolved is removed wherever it appears - quoted in a log line, echoed in
      an error, embedded in a config dump - without depending on the credential looking like
      anything in particular. The placeholder NAMES the reference, so a human reading the transcript
      sees which secret was removed without seeing it.
  - id: AC3
    text: >
      CREDENTIAL SHAPES ARE A SECOND, BEST-EFFORT PASS, REUSING THE GATE'S OWN DETECTORS rather than
      reimplementing them. It covers secrets the runtime never resolved and therefore cannot know by
      value - somebody else's token in a log the responder is reading. Two spellings of "what a
      secret looks like" would drift, and the one that drifted would be this one. Declared
      best-effort because it is.
  - id: AC4
    text: >
      FAIL CLOSED: IF A KNOWN VALUE SURVIVES, THE WHOLE CHUNK IS REFUSED. A partially redacted string
      is worse than none, because it looks scrubbed. The seam re-checks its own output for every
      known value and raises rather than returning a best effort, which catches a replacement bug in
      its own loop instead of trusting it.
  - id: AC5
    text: >
      THE PLACEHOLDER IS NOT LENGTH-PRESERVING, DELIBERATELY. A fixed-width mask would let an
      observer read the secret's length off the transcript, and length identifies the provider.
      Ordinary content is untouched: a selftest asserts a git sha in the same blob survives, because
      a seam that mangles normal data gets bypassed and then protects nothing.
required_evidence: [unit]
rollback: >
  Delete the module and its capability entry. It is a pure text transform, holds nothing beyond the
  call, and no caller depends on it yet.
---

## Outcome

Everything an agent reads passes through one seam, and secrets are removed there.

## Why upstream and not afterwards

Once a credential is in a model's context it is in the transcript, in whatever the model quotes
back, in any summary it writes, and in the compaction that follows. There is no recall. Filtering
the transcript afterwards addresses the copy you can see and none of the copies you cannot.

So the removal has to be upstream of the boundary. **A context that never held a secret cannot leak
one**, and that is the whole argument.

## Two passes, and only one of them is reliable

**Known values** are redacted by value. Whatever the runtime resolved gets removed wherever it
turns up, regardless of whether it looks like a credential. This is the pass that protects you.

**Credential shapes** are a second, best-effort pass for secrets the runtime never resolved and so
cannot know by value - somebody else's token in a log the responder happens to be reading. It reuses
the gate scanner's detectors rather than restating them, because two definitions of "what a secret
looks like" drift apart and the one that drifts is always the copy.

Saying which pass is reliable matters more than the passes. An operator who believes shape detection
is the protection will eventually store a credential that matches no pattern.

## Failing closed, and the length of the mask

If a known value survives its own redaction, the seam refuses the chunk rather than returning
something that looks scrubbed. And the placeholder is not length-preserving, because a fixed-width
mask leaks the length, and length identifies the provider.
