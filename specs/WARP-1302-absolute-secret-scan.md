---
schema: veldo.spec/v1
id: WARP-1302
title: Pattern plus entropy over everything, failing closed with no allowlist mechanism at all - which
  is only defensible because W1 removed every legitimate reason to hold a literal credential
status: shipped
risk: standard - a pure scanner that reads text and reports. It is not low because a scanner too
  permissive lets a credential into history where deleting it does not remove it, and one too noisy
  gets disabled, which produces the same outcome by a slower route.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0013
work: W2
depends_on: [WARP-1301]
placement: [enforcement]
footprint:
  - ".veldo/secret_scan.py"
  - "engine/.veldo/secret_scan.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/01_warp_0101_reviewer_notes.py"
  - "specs/WARP-1302-absolute-secret-scan.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      TWO DETECTORS, BECAUSE EACH CATCHES WHAT THE OTHER MISSES. Patterns catch known provider
      shapes and structural markers; entropy catches the unknown provider whose format nobody has
      written a pattern for yet. A selftest drives one seeded example per secret class - private key,
      Stripe, GitHub, Slack, AWS, Google, JWT, literal assignment - and a high-entropy token matching
      no pattern.
  - id: AC2
    text: >
      THERE IS NO ALLOWLIST MECHANISM, AND THE REFUSAL SAYS WHY. Every secret scanner ships with an
      exemption list and every one rots into a tunnel: the first entry is a fixture, the tenth is a
      real credential somebody was in a hurry about. The exemption exists because normal codebases
      have legitimate literal credentials; W1 removed that, so the exemption has nothing to be for.
      A selftest asserts no allowlist, ignore-file or skip-comment mechanism exists in the module,
      and that the refusal text explains the absence so a reader hitting a false positive finds the
      reason rather than concluding the tool is broken.
  - id: AC3
    text: >
      THE ONE STRUCTURAL EXCLUSION IS A SHAPE RULE, NOT A LIST. Pure hex at a known digest width is
      excluded, because git object ids and sha256 digests fill this repository's own proofs, are
      derived from public content, and are not credentials. It is a rule about shape, never a set of
      blessed strings, which is exactly the difference that stops it rotting into an allowlist by
      another name. A selftest drives a real git sha and a sha256 to clean.
  - id: AC4
    text: >
      UNREADABLE IS NOT CLEAN. A file the scanner cannot read is reported, never skipped, because
      passing it silently is how a binary blob becomes the hiding place.
  - id: AC5
    text: >
      A FALSE POSITIVE IS RESHAPED, NEVER EXEMPTED, and the refusal says how: shorten the sample,
      make it obviously fake, or move it behind a reference. Minutes of work at machine prices,
      against a credential in git history that deleting does not remove.
required_evidence: [unit]
rollback: >
  Delete the module and its capability entry. It reads text and returns findings; no state, no gate
  wiring yet, no behaviour change.
---

## Outcome

Pattern plus entropy over every diff, every generated file and every recorded artifact, failing
closed.

## The only interesting decision: no allowlist

Every secret scanner ships with an exemption mechanism, and every one of those lists rots. The first
entry is a test fixture. The tenth is a real credential somebody was in a hurry about. Nobody
re-reads it, and the file that was supposed to make the check usable is the file that makes it
useless.

The exemption exists because in a normal codebase there are legitimate reasons to hold a literal
credential-shaped string. **W1 removed those reasons.** A secret is a reference. A literal has no
legitimate place in any file, so an exemption would have nothing to be for except the exact case
this check exists to catch.

That is only defensible because of W1, and the refusal text says so out loud, because the first
person to hit a false positive will go looking for the exemption and needs to find the reason it
was not built rather than concluding the tool is broken.

## The one exclusion, and why it is not an allowlist in disguise

Pure hex at a known digest width. Git object ids and sha256 digests are everywhere in this
repository's own proof artifacts, they are derived from public content, and they cannot be
credentials.

It is a rule about SHAPE, not a set of blessed strings. That is the whole difference: a shape rule
cannot accumulate entries, cannot be edited in a hurry to make a build pass, and cannot quietly come
to contain a real secret.
