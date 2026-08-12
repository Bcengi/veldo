---
schema: veldo.spec/v1
id: WARP-0623
title: The codified live provisioner cannot run at all - an instance attribute permanently shadows a
  provisioning method, so fix the collision AND add the structural check that would have caught it,
  because an offline fake that defines the same private names as the real adapter can hide a name
  collision forever (hardening of the PLAN-0016 live edge, found on the first real execution)
status: shipped
risk: standard - a rename of one private method and its three call sites, plus a new structural check.
  It touches no protected path, no safety core, no contract and no gate stage; it changes no behavior any
  passing test asserts, because the code path it repairs currently raises TypeError on every call and is
  therefore unreachable in any green state. The footprint tier is standard: a single declared area,
  tracker, via .veldo/tracker_jira_live.py, with .veldo/tracker_intake.py read for the constructor and NOT
  edited. It is worth reviewing carefully for one reason only: the FIX is trivial and the CHECK is the
  actual deliverable, so a reviewer should attack whether the check genuinely catches the class rather
  than only this instance
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: []
placement: [tracker]
footprint:
  - .veldo/tracker_jira_live.py
  - .veldo/capabilities.yaml
  - engine/.veldo/capabilities.yaml
  - packs/*/.veldo/capabilities.yaml
  - scripts/selftest.py
  - specs/WARP-0623-live-provisioner-name-collision.md
  - specs/index.md
protected_paths: []
behavior_bearing: true
observability:
  logs: No new logging surface. The repaired path reports through the existing provisioner errors, and the
    new structural check reports each shadowed name BY NAME (the class, the attribute, and the method it
    hides) so a future collision is diagnosable from the check output alone.
  error_taxonomy: The check's single failure class is SHADOWED_PROVISIONER_METHOD, naming the exact
    class, the instance attribute set in the constructor, and the method it makes unreachable; the repaired
    provisioning path raises the pre-existing provisioner error classes unchanged.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Rename the mixin method _project_record back to _project at .veldo/tracker_jira_live.py:104 with its
      two call sites at lines 118 and 127, restoring the collision with the self._project the base
      constructor sets at .veldo/tracker_intake.py:473, and the reproduction at
      scripts/suites/13_warp_0623_codified_live.py:48 (every mixin method callable on the REAL composed
      instance, with a project key and without) plus the guard assertion at line 53 must go red, the guard
      returning ['_project'] again. Reachability on the real composition, never on the fake, is the
      load-bearing leg: the same reproduction run against a FakeTracker cannot fail in either direction.
    text: >
      THE DEFECT IS REPRODUCED BEFORE IT IS FIXED, as a test that FAILS on the current code. A selftest
      constructs the REAL adapter (the shipped JiraCloudAdapter composed with the live provisioning mixin,
      not the FakeTracker) and asserts that the provisioning method the mixin defines is CALLABLE on that
      instance. On the code as shipped this assertion fails, because JiraCloudAdapter.__init__ sets
      self._project (the project key, default None) and the mixin defines a method _project(self,
      project_key), so the attribute permanently shadows the method and every provisioning call raises
      TypeError ("str object is not callable" when a project is configured, "NoneType object is not
      callable" when it is not). The reproduction is recorded as the evidence that the fix fixes something
      real, and it is written so it would have failed on every commit since the collision was introduced.
  - id: AC2
    falsified_by: >
      Fix the collision the other way instead: rename the constructor attribute at
      .veldo/tracker_intake.py:473 from self._project to self._project_key and give the mixin its _project
      name back, and the assertion at scripts/suites/13_warp_0623_codified_live.py:80 must go red on both
      of its halves, the literal `self._project = project` no longer being in the intake source and
      _lp_with_key._project no longer holding the configured key. WHICH SIDE gets renamed is the
      load-bearing leg, because both directions make the method callable and only this one leaves the
      configured project key readable by the shipped code that already reads it.
    text: >
      THE COLLISION IS FIXED BY RENAMING THE METHOD, not by renaming the attribute or by deleting either.
      The mixin's _project becomes a distinct name (_project_record) and its call sites inside
      .veldo/tracker_jira_live.py are updated; the constructor attribute self._project keeps its name and
      meaning, because it is the configured project key that other shipped code reads and renaming it
      would be a wider change than the defect warrants. .veldo/tracker_intake.py is READ and NOT edited. The
      renamed method's behavior is byte-for-byte the same logic (fetch the project record from the REST
      endpoint and cache its id); nothing about the REST shapes, the caching, or the error classes changes.
      A selftest asserts the old name is GONE from the mixin (so the collision cannot silently return) and
      that no other module references it.
  - id: AC3
    falsified_by: >
      Replace the runtime intersection in shadowed_provisioner_methods (.veldo/tracker_jira_live.py:604,
      `for name in sorted(methods & attributes):`) with the hardcoded pair `sorted({"_project"} &
      attributes)`, and the FUTURE-collision assertion at
      scripts/suites/13_warp_0623_codified_live.py:164 must go red while the historical seed at line 154
      still refuses, which is exactly the assertion that separates a generic check from a named-pair one.
      Genericity over the composition is the load-bearing leg named by the criterion itself; the refusal
      leg falsifies separately by removing the `if findings:` raise at line 628-629, reddening line 287.
    text: >
      THE STRUCTURAL CHECK IS THE REAL DELIVERABLE, because this class of defect is invisible to the
      offline suite by construction: the FakeTracker defines its OWN _project method and is constructed
      WITHOUT a project key, so the collision is UNREACHABLE in the gate no matter how many fixtures run.
      A new check enumerates, for the real adapter composition, every METHOD the live provisioning mixin
      defines and every INSTANCE ATTRIBUTE the constructor sets, and REFUSES BY NAME
      (SHADOWED_PROVISIONER_METHOD) on any intersection, reporting the class, the attribute and the hidden
      method. It is generic over the composition rather than a hardcoded list of the current names, so a
      NEW collision introduced by a future constructor field or a future mixin method is caught without
      anyone remembering to look. A selftest proves it: with a seeded synthetic collision the check
      REFUSES and names it; with the collision removed the check passes; and the check is asserted to
      report EMPTY against the fixed real composition.
  - id: AC4
    falsified_by: >
      Make the two guards dependent: replace the callability loop in unreachable_provisioner_methods
      (.veldo/tracker_jira_live.py:641-645) with a try/except around
      check_provisioner_composition(type(instance), instance=instance) that returns the shadowed names off
      the refusal, and the EXACTLY DIAGONAL assertion at
      scripts/suites/13_warp_0623_codified_live.py:298 must go red, because neutralizing the shadow
      refusal now also silences the callability fixture and the off-diagonal cell turns True. Independence
      of the two guards is the load-bearing leg: a matrix whose guards share a mechanism proves one tooth.
    text: >
      THE TEETH ARE A MATRIX, the standard this repository adopted after WARP-1208's round-2 review. The
      guards under teeth are the shadow check itself and the reproduction assertion of AC1: each is
      neutralized IN MEMORY one at a time and run against every guard's fixture, the resulting matrix is
      asserted EXACTLY DIAGONAL, each mutation target is asserted to appear exactly once in its module, and
      every module on disk is asserted sha256-unchanged after all runs. The CONTROLS prove no over-firing:
      a legitimate attribute whose name merely RESEMBLES a method name (a _project_key attribute beside a
      _project_record method) does NOT refuse, and a mixin method that no constructor attribute shadows
      does not refuse. The honest boundary, labeled review-lane: the check finds NAME collisions on the
      composed class, not every way a live path can be unreachable (a wrong endpoint, a wrong payload
      shape, or a permission the credential lacks are only found by executing it, which is WARP-0620).
  - id: AC5
    falsified_by: >
      Overclaim the record: change `scope: repo-only` to `scope: engine` in the
      tracker_provisioner_shadow_check entry at .veldo/capabilities.yaml:172 and drop the sentence holding
      the live path UNEXECUTED until WARP-0620 from that same entry, and the assertion at
      scripts/suites/13_warp_0623_codified_live.py:332 must go red on both of its named substrings. The
      honest scope-and-UNEXECUTED record is the load-bearing leg, because it is the one that stops a reader
      taking a name-collision check for the live proof; the byte-identity leg falsifies separately by
      making that edit in engine/.veldo/capabilities.yaml alone, which reddens line 326.
    text: >
      ADDITIVE AND HONESTLY RECORDED, with the lesson written where it will be read.
      CORRECTED PREMISE (this criterion was wrong as first written and the correction is the honest
      record): .veldo/tracker_jira_live.py has NEVER been part of the canonical engine. engine/.veldo
      carries tracker.py and trackers.json and no other tracker module, and the pack engine set is DERIVED
      from what exists there, so creating a copy would make an orphan Jira provisioner an engine file every
      pack must carry without its adapter base or its orchestrator. The original text demanded a
      byte-identical sync of a module that does not ship, and satisfying it literally would have shipped
      that orphan to adopters. What IS required and proven: .veldo/capabilities.yaml, which IS in the engine
      set, carries the new entry byte-identical across all eight copies; the entry is marked scope repo-only,
      which is exactly what this repository's own capabilities-honesty check demands of an entry whose home
      does not resolve in the shipped engine (the same marking its siblings tracker_board_bootstrap,
      tracker_agent_identity and tracker_board_snapshot carry); a selftest asserts that repo-only truth
      mechanically so the record cannot drift into overclaiming; and template sync and pack drift both end
      empty. No existing assertion is weakened or deleted and the selftest count
      only grows. capabilities.yaml records the shadow check as a mechanical capability and states plainly
      that the live provisioning path itself remains UNEXECUTED against a real board until WARP-0620, so no
      reader can mistake this item for the live proof. The full gate is GREEN, RULE #1 is clean, no
      protected path is touched, and the safety core is untouched. The module docstring records WHY the
      collision survived: the offline fake defines the same private names as the real adapter, so
      "codified from a proven script" is not the same as "the codified path ran".
required_evidence: [unit]
rollback: >
  Revert the commit. The change renames one private method inside .veldo/tracker_jira_live.py and its three
  call sites, adds a structural shadow check plus its selftests, and adds one capabilities entry, all
  with the capabilities entry re-synced byte-identical across engine and the packs (the live module
  itself is repo-only and ships in no pack). Reverting restores the collision, which
  means the live provisioning path returns to raising TypeError on every call - it does not restore any
  working behavior, because there is none to restore. Nothing else reads the renamed method, the
  constructor attribute is untouched, and no contract, gate stage or record changes, so there is no
  migration and nothing to unwind.
---

## Intent

The first genuine attempt to execute the codified live provisioner against a real Jira board found that it
cannot run at all. Not in an edge case: on every call, in every configuration. The adapter constructor
sets an instance attribute named _project holding the configured project key, and the live provisioning
mixin defines a method with the same name, so the attribute permanently shadows the method and every
provisioning call raises TypeError. It fails one way with a project configured and another way without
one, which is how it was proven rather than guessed.

The one-line rename is not the point of this item. The point is why a module that was carefully written
from REST shapes proven by a working script could sit in the repository, fully synced across nine copies,
covered by a green gate, and be unrunnable. The offline FakeTracker defines its own _project method and is
constructed without a project key, so the collision is structurally unreachable in the test suite. No
number of additional fixtures would have found it. That is a hole in the shape of the tests, not a gap in
their quantity, and the deliverable here is the check that closes it for the whole class.

The lesson generalizes past this defect and belongs in the record: codified from a proven script is not
the same as the codified path ran. A live-path module has not been proven by anything until it has been
executed once for real, and a fake that mirrors the real object's private names can hide a collision
forever.

## Context

- How it was found: pointing a sandbox tracker entry at a throwaway board and running the codified
  bootstrap. It died before touching Jira, twice, with the two different TypeErrors that prove the
  shadowing is unconditional rather than configuration-dependent.
- What is NOT broken, so the scope stays honest: the real board provisioned earlier is fine, its fence is
  live, and the two identity groups are correct (the agent group holds only the service account, the
  approver group holds only the founder, and only the three terminal transitions carry conditions). The
  REST shapes inside the module are proven by the script that did that work. It is the reusable codified
  path that has never run.
- Why the check is generic rather than a named-pair assertion: a hardcoded "assert _project is callable"
  would pass forever after this rename and catch nothing new. The next constructor field or mixin method
  that collides would reintroduce exactly this failure. The check therefore intersects the constructor's
  attribute names with the mixin's method names on the composed class, which is decidable statically and
  costs nothing to run.
- What this item deliberately does NOT claim: that the live path WORKS. It claims only that the path is
  reachable and that this class of unreachability is now checked. Whether the endpoints, payloads and
  scopes are right is decided by executing it against a real board, which is WARP-0620 and needs the
  founder present.

## Out of scope

- No live execution and no board mutation. This item is offline: a rename, a check, and selftests.
- No change to the constructor, to .veldo/tracker_intake.py, or to the meaning of the configured project
  key.
- No change to any REST shape, endpoint, payload, retry or error class in the provisioning path.
- No fix for any other live-path defect. If executing the repaired path later reveals a wrong endpoint or
  a missing scope, that is WARP-0620's finding and its own item; this spec does not pre-empt it.
- No protected path, no safety core, no contract, no gate stage.

## Notes

- Write the reproduction FIRST and watch it fail, then rename, then watch it pass. A test written after
  the fix tends to assert the fix rather than the defect.
- Make the shadow check enumerate from the composed class at runtime rather than from a literal list, and
  assert in a selftest that a SEEDED synthetic collision is caught. A check that cannot be shown to refuse
  is decoration.
- Put the controls in: an attribute whose name merely resembles a method name must not refuse, or the
  check will be disabled by the first false positive someone hits.
- Record the reason in the module docstring, not only in this spec. The next person to add a fake that
  mirrors the real adapter's private names needs to read it there.
- RULE #1 clean (ASCII hyphen only, no em dash, no en dash, no prose double-hyphen).
