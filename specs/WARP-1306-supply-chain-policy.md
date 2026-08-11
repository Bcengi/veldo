---
schema: veldo.spec/v1
id: WARP-1306
title: A new dependency arrives attached to a reason or it does not arrive - because an agent picks
  packages by familiarity from training data, which is trivially poisoned
status: shipped
risk: standard - a pure checker over two manifests and a lockfile. It is not low because it decides
  what enters the dependency tree, and permissive here is a typosquat landing in seconds inside a
  change about something else.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0013
work: W6
depends_on: []
placement: [enforcement]
footprint:
  - ".veldo/supply_chain.py"
  - "engine/.veldo/supply_chain.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/01_warp_0101_reviewer_notes.py"
  - "specs/WARP-1306-supply-chain-policy.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      AN ADDED DEPENDENCY WITHOUT A RECORDED DECISION REFUSES. The requirement is VISIBILITY, not
      review quality: a dependency arrives attached to a reason or it does not arrive. A selftest
      drives a bare addition to a refusal and the same addition with a decision reference to clean.
  - id: AC2
    text: >
      A VERSION BUMP IS NOT AN ADDITION, and this is what keeps the check from being removed.
      Bumping something already decided is ordinary work; flagging it as a new decision would make
      the check so noisy somebody deletes it. What is new is the RELATIONSHIP, not the number.
  - id: AC3
    text: >
      THE SOFT SEAM (C6) STANDS DOWN TO A WEAKER ARTIFACT, NEVER TO NOTHING. Where PLAN-0011's
      decision records exist a `DEC-` reference is required and RESOLVED against them, so a
      reference to a record that does not exist refuses. Where they do not exist, a written reason
      of real length satisfies the same requirement. Supplying neither refuses: standing down to
      nothing would disable the check in exactly the repositories least able to afford it.
  - id: AC4
    text: >
      LOCKFILE INTEGRITY IS CHECKED SEPARATELY FROM POLICY, AND BOTH FAIL CLOSED. An entry with no
      hash pins a NAME rather than a package. A dependency in the manifest but absent from the
      lockfile means somebody edited one and not the other, which is how a resolved version drifts
      from a declared one. A repository can have a good reason for every dependency it holds and
      still install whatever the registry serves today.
  - id: AC5
    text: >
      AN UNDECLARED LICENSE IS REFUSED, NOT ASSUMED PERMISSIVE. A dependency whose license nobody
      recorded is one nobody checked, and the permissive assumption is how a copyleft package ends
      up in a proprietary product. The permitted set is policy data, not code.
required_evidence: [unit]
rollback: >
  Delete the module and its capability entry. It reads two dicts and returns findings; no state, no
  gate wiring yet, no behaviour change.
---

## Outcome

A new dependency is a decision somebody made, not a convenience that appeared.

## Why this is different for agents than for people

A person adding a dependency has usually at least glanced at it. An agent picks packages the way it
picks patterns: by familiarity from training data. That is a completely different selection
function, and it is trivially poisoned - a package named plausibly enough to look familiar is the
entire mechanism of a typosquat.

And the agent adds it in seconds, in the middle of a change about something else, under a commit
message about the something else. Nobody is being careless. The dependency simply never surfaces as
a thing that was chosen.

So the requirement is visibility rather than review quality: a dependency arrives attached to a
reason, or it does not arrive.

## What this deliberately does not flag

Version bumps. Bumping a dependency you already decided to take is ordinary work, and treating each
bump as a fresh decision would make the check noisy enough that somebody removes it - at which point
it protects nothing. What is new is the relationship, not the number.

## Standing down without standing aside

Where PLAN-0011's decision records exist, a `DEC-` reference is required and resolved against them.
Where they do not, a written reason of real length does the job.

Standing down to a weaker artifact is correct. Standing down to nothing would make the check
optional in precisely the repositories with the least machinery, which are the ones most likely to
acquire a dependency nobody chose.
