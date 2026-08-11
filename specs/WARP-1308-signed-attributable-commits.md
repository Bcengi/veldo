---
schema: veldo.spec/v1
id: WARP-1308
title: Git says "good signature" for any key the local keyring holds, and the keyring is a file in
  the environment the agent runs in - so the fingerprint is pinned against a registry in the repo
status: shipped
risk: high - this decides whether a commit is attributable at all. Permissive here is an attacker
  adding a key to a keyring and every commit they make verifying beautifully, which is the failure
  mode that looks most like success.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0013
work: W8
depends_on: []
placement: [enforcement]
footprint:
  - ".veldo/commit_attribution.py"
  - "engine/.veldo/commit_attribution.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/01_warp_0101_reviewer_notes.py"
  - "specs/WARP-1308-signed-attributable-commits.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      A GOOD SIGNATURE FROM AN UNREGISTERED KEY REFUSES. `git verify-commit` reports G for any key
      the local keyring holds; a local keyring is a file in the environment the agent runs in, so an
      attacker who can write a commit can usually also add a key. The fingerprint is pinned against
      a registry declared in the repository, and the selftest drives a perfectly good signature from
      an unknown key to a named refusal.
  - id: AC2
    text: >
      THE TRAILER IS A CLAIM AND THE SIGNATURE IS WHAT MAKES IT EVIDENCE. Signed-but-unattributed
      and attributed-but-unsigned refuse with DIFFERENT reasons, because they are different
      failures. A commit whose trailer names one actor while the signing key belongs to another
      refuses with a third.
  - id: AC3
    text: >
      IT FAILS CLOSED ON ANY STATE THAT IS NOT AN EXPLICIT GOOD. Git has several verification states
      and has gained more over time. Expired, revoked, unknown-validity and unrecognised states all
      refuse, so a state this check has never heard of cannot be the one that lets a commit through.
  - id: AC4
    text: >
      ONLY THE LAST PARAGRAPH'S TRAILERS COUNT, which is what git itself means by a trailer. A
      `Veldo-Agent:` line quoted in the middle of a body is prose; honouring it would let a commit be
      attributed by quoting an earlier one. A selftest drives exactly that and it does not attribute.
  - id: AC5
    text: >
      ENFORCEMENT IS CONFIGURABLE AND ON FROM FIRST RELEASE (D3), AND THE CHECKS RUN EITHER WAY. With
      enforcement off the findings are still produced and still reported, and `refuses()` returns
      False. A check switched off entirely goes stale, and the day somebody enables it they meet a
      wall of findings and switch it straight back off.
  - id: AC6
    text: >
      EVERY COMMIT IN THE RANGE IS CHECKED, NOT THE TIP. A range merges as a unit, so an unsigned
      commit three back merges just as thoroughly as the one on top.
required_evidence: [unit]
rollback: >
  Delete the module and its capability entry. It reads parsed commit records and returns findings;
  it signs nothing, runs no git, and is not yet wired into the gate.
---

## Outcome

Every commit names the actor that produced it, and a signature by a key the repository declares is
what turns that name into evidence.

## The thing that is easy to get wrong

The obvious implementation asks git whether the signature is good and believes the answer. Git
answers about the local keyring: it reports a good signature for a key that keyring happens to hold.
That keyring is a file, in the environment the agent is running in, and anyone who can author a
commit there can usually add a key to it. At that point every commit they make verifies, and the
verification is worse than none because it produces confidence.

This is the WARP-0730 lesson arriving in a second place. The predicate has to live somewhere the
thing being checked cannot reach - so the signing fingerprint is pinned against a registry declared
in the repository, under the protected-path rules, where changing it is a reviewed change rather
than a step in an attack.

## Two different failures, two different refusals

`Veldo-Agent: builder-3` is a line of text. Anybody can type it, including the agent that would like
to be somebody else. The trailer says who; the signature is the only part that says the who is true.
So an unsigned commit and an unattributed commit do not collapse into one "policy violation" - they
are different problems with different fixes, and a gate that names them identically is a gate people
learn to skim.

## On from the start, running either way

Enforcement is configurable and on from the first release (D3). With it off the checks still run and
still report; they simply do not block. A check that is disabled entirely goes stale, and whoever
eventually enables it meets a wall of accumulated findings and disables it again.
