---
schema: veldo.spec/v1
id: WARP-0626
title: Make the shadow check cover the CLASS it claims to - a class-level attribute makes a provisioning
  method just as unreachable as an instance one and neither wired site refuses it, the function that
  catches it already sits in the file wired to nothing, and wiring it also removes both known false
  positives (hardening of WARP-0623, from its own review's ranked notes)
status: ready
risk: standard - this strengthens a REFUSAL and removes two false positives. It can only refuse more where
  a method is genuinely unreachable and less where a method is genuinely callable, which are both the
  correct directions. It touches the live provisioning module and the adapter base, no protected path, no
  safety core, and no gate stage. It is worth reviewing carefully for one reason: this item exists because
  the previous one claimed to "close the whole class of defect" and did not, so a reviewer should test the
  class claim rather than the instance
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: [WARP-0623]
placement: [tracker]
footprint:
  - .veldo/tracker_jira_live.py
  - .veldo/tracker_adapter.py
  - .veldo/capabilities.yaml
  - engine/.veldo/capabilities.yaml
  - packs/*/.veldo/capabilities.yaml
  - scripts/selftest.py
  - specs/WARP-0626-shadow-check-covers-the-class.md
  - specs/index.md
protected_paths: []
behavior_bearing: true
observability:
  logs: The refusal names WHICH mechanism decided it - a name intersection, or a resolved attribute that is
    not callable - and names the class, the shadowing source and the hidden method, so a refusal is
    diagnosable without reading the source and a false positive is recognizable as one.
  error_taxonomy: The names stay closed and gain one: SHADOWED_PROVISIONER_METHOD (a declared attribute
    name intersects a provisioning method name) and UNREACHABLE_PROVISIONER_METHOD (the resolved attribute
    on a real instance is not callable, whatever shadowed it), plus the pre-existing vacuity refusal for a
    composition in which no provisioning mixin is recognized.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Move the shadowing class attribute in each of the three reproduction fixtures onto an MRO layer BEHIND
      the mixin instead of ahead of it, so getattr resolves to the provisioning method again, and the
      reproduction assertion that every call raises TypeError must go red for all three shapes; that assertion
      is the load-bearing leg, because it is what proves the shapes are genuinely unreachable rather than
      merely name-colliding.
    text: >
      THE DEFECT THE PREVIOUS ITEM MISSED IS REPRODUCED FIRST, in all three shapes its reviewer found: a
      CLASS ATTRIBUTE on a layer ahead of the mixin, a class attribute stamped onto the composed class, and
      an UNASSIGNED __slots__ entry ahead of the mixin. In each, a provisioning method is genuinely
      unreachable and every call raises TypeError exactly as the historical collision did, and the shipped
      check as it stands REFUSES NONE OF THEM. These assertions FAIL on the code as shipped and are the
      evidence that "close the whole class of defect" was an overstatement rather than a description.
  - id: AC2
    falsified_by: >
      Delete the unreachable_provisioner_methods(self) call from the per-instance branch so
      check_provisioner_composition (.veldo/tracker_jira_live.py:613) refuses on the name intersection alone,
      and the selftest that a class attribute hiding a provisioning method is refused as
      UNREACHABLE_PROVISIONER_METHOD must go red while the name-intersection selftest stays green.
    text: >
      THE CALLABILITY PROBE IS WIRED, which is strictly stronger than intersecting names because it asks
      the only question that matters: does the resolved attribute on a real instance actually call. The
      function that answers it already exists in the module (unreachable_provisioner_methods) and is wired
      into nothing, which is why the previous item's manifest counting it as one of two shipped guards was
      an overstatement of the defence in depth by a factor of two. It is now called on the per-instance
      path, refusing UNREACHABLE_PROVISIONER_METHOD by name and reporting the class, what shadowed the
      method and which method it hid. The name-intersection check is RETAINED, because it catches a
      declared collision before an instance exists and the two together are a superset of either.
  - id: AC3
    falsified_by: >
      Drop the callability veto from the per-instance path so any name in methods & attributes refuses again
      (.veldo/tracker_jira_live.py:594), and the two selftests asserting the callable retry-wrap override
      PASSES and the uncalled-base-__init__ attribute PASSES must both go red, along with the assertion that
      their old refusal names are absent.
    text: >
      BOTH KNOWN FALSE POSITIVES DISAPPEAR, and that is the same change rather than a second one. A
      constructor that assigns a CALLABLE over a mixin method's name - the ordinary per-instance override
      or retry-wrap idiom - is no longer refused, because the resolved attribute calls; the previous
      behaviour refused it while asserting in the message that every call raises TypeError, which was
      simply false of that instance. And an attribute set by a base __init__ that the composed constructor
      never calls is no longer refused at class level, because the instance does not carry it and the
      method stays callable. Selftests prove both shapes now PASS, and prove the refusals they used to
      produce are gone by name. This matters more than it looks: the first false positive is what gets a
      check deleted by the next person it inconveniences.
  - id: AC4
    falsified_by: >
      Delete __init_subclass__ from _CompanyManagedProvisionerOps and leave the check only on
      make_company_managed_provisioner (.veldo/tracker_jira_live.py:660), and the selftest that a hand-rolled
      composition built directly from the exported mixin without the factory is refused must go red; the
      lineage binding is the load-bearing leg, the truthy-marker widening in _is_provisioner_ops is the lesser
      one and reddens by restoring the `is True` identity test.
    text: >
      THE CHECK BINDS TO THE MIXIN LINEAGE, NOT TO ONE FACTORY, so it cannot be forgotten by construction
      rather than by discipline. Both wired sites currently live on the factory, so a composition built
      directly from the exported mixin is checked at neither, which the previous item's manifest described
      as "wired where it cannot be forgotten". The check moves onto the mixin itself via __init_subclass__,
      so every composition in the lineage is checked at class-creation time however it was built, and a
      selftest proves a hand-rolled composition that bypasses the factory entirely is now refused. The
      marker test also stops being brittle by one character: a truthy marker is honoured rather than only
      the exact True, so a future layer writing a different truthy value does not silently drop out of the
      enumeration.
  - id: AC5
    falsified_by: >
      Remove the _PROVISIONER_OPS marker from FakeTracker so the check refuses it for vacuity instead of
      inspecting it, and the selftest that plants the historical _project collision on the FAKE side and
      expects a named refusal must go red; separately, deleting any one off-diagonal row must redden the
      empty-list assertion in the teeth matrix.
    text: >
      THE FAKE IS INSIDE THE CHECK, which closes the loop on how this whole defect class stayed invisible.
      The FakeTracker's private-name mirroring of the real adapter is what made the original collision
      unreachable in the gate, and it is currently outside the check entirely: it carries no marker, so the
      check refuses it for vacuity rather than inspecting it, while it already holds an attribute one
      character away from its own method of nearly the same name. The fake is brought into the check's
      scope so a collision introduced on the fake side is caught too, and a selftest proves that adding
      the historical collision to the FAKE is now refused. Anti-vacuity per the house standard: teeth as a
      MATRIX over every guard (name intersection, callability probe, lineage binding, vacuity refusal),
      exactly diagonal with the off-diagonal asserted as an EMPTY LIST, every mutation target unique, every
      touched module sha256-unchanged, and the finest-grained site chosen per guard with the reason in a
      comment.
  - id: AC6
    falsified_by: >
      Delete one member from the module's declared shape enumeration, the unassigned __slots__ entry, without
      touching the tests that exercise it, and the selftest asserting the module enumeration equals the set
      the tests drive must go red on the missing member rather than passing with a smaller class.
    text: >
      THE DECLARED SHAPE GAPS ARE ENUMERATED RATHER THAN LEFT AS FOLKLORE, applying the lesson this
      repository paid for twice: when a check claims a class, the class members are listed and each is
      either covered or declared uncovered with its reason. The enumeration covers at minimum an
      instance attribute, a class attribute on any MRO layer, a stamped class attribute, an unassigned
      __slots__ entry, a name-mangled attribute, a dunder-named method, a non-data descriptor whose object
      is not callable, a nested-class name, a setattr after construction, and a subclass that re-shadows.
      Each is asserted either REFUSED or explicitly DECLARED out of scope with the reason, and a selftest
      asserts the enumeration in the module matches the one the tests exercise, so a member cannot be
      quietly dropped. capabilities.yaml is corrected in every copy: the entry stops claiming the whole
      class and states exactly which shapes are refused. The full gate is GREEN, RULE #1 clean, no
      protected path touched, and the frozen safety core byte-UNCHANGED.
required_evidence: [unit]
rollback: >
  Revert the commit. The change wires an existing function into the per-instance path, moves the check onto
  the mixin lineage, widens the marker test, brings the fake into scope, adds one refusal name and an
  enumeration, and corrects one capabilities entry, all re-synced byte-identical across engine and
  the packs. Reverting restores a check that misses class-level shadows and produces two false positives, so
  it is a regression in both directions rather than a return to a good state. No record, event, contract or
  write path changes, so there is no migration.
---

## Intent

WARP-0623 fixed a collision that made the codified live provisioner unrunnable, and shipped a generic check
so the next one would be caught. Its own reviewer then found that the check catches the NAME-INTERSECTION
class and not the class it claimed: a class-level attribute, a stamped class attribute, or an unassigned
slot ahead of the mixin each make a provisioning method exactly as unreachable, raise exactly the same
TypeError, and are refused by neither wired site. The function that catches all three already sits in that
module, wired to nothing.

So this item is the same lesson this repository paid for twice today in a different module: when a review
names a defect CLASS, enumerate the members and cover them, or declare in writing which ones you are not
covering and why. The previous manifest said "close the whole class of defect", which was an overstatement
a reviewer refuted in three probes.

The most useful property of the fix is that it is one change closing three notes. Asking whether the
resolved attribute actually CALLS is strictly stronger than asking whether two names collide, and it is
also strictly kinder: the two false positives the current check produces both disappear, because in both of
them the method is genuinely callable. A check that refuses correct code is a check someone deletes.

## Context

- The three shapes the 0623 reviewer reproduced, and which this item must refuse: a class attribute on an
  MRO layer ahead of the mixin, a class attribute stamped onto the composed class, and an unassigned
  __slots__ entry. In each case getattr resolves to something that is not callable, or raises, and the
  existing name-intersection check sees nothing because no constructor declares the name.
- The two false positives, and why they are the same fix: a constructor assigning a CALLABLE over a mixin
  method name is the ordinary override idiom and the method still calls; an attribute set by a base
  __init__ that the composed constructor never invokes never reaches the instance. Both are refused today,
  and the refusal message asserts the call raises when it demonstrably does not.
- Why the binding moves to the lineage: both wired sites are on the factory, so any composition built
  directly from the exported mixin is unchecked. There is exactly one production composition today, which
  is why this is a future-facing gap rather than a live hole, and __init_subclass__ makes it structural
  instead of a convention someone must remember.
- Why the fake must be in scope: the FakeTracker's mirroring of the real adapter's private names is the
  reason the original collision was unreachable in the gate. Leaving the fake outside the check preserves
  the exact blind spot that produced the defect, on the other side of the seam.

## Out of scope

- No change to the rename itself, which is correct and shipped.
- No live board call. This item is entirely offline.
- No attempt to detect a method made unreachable by something other than a shadowing attribute or
  descriptor on the composed class: a monkeypatch applied after construction, or a C-level replacement, is
  declared out of scope with the reason (nothing re-checks after construction, which is inherent).
- No protected path, no safety core, no contract, no gate stage.

## Notes

- Write the three reproductions FIRST and watch them fail. This item exists because a claim was written
  ahead of the evidence, so the evidence goes first this time.
- The enumeration is the deliverable as much as the wiring is. A check that covers ten shapes and lists
  them is worth more than one that covers eleven and lists none, because the next person can see the
  boundary.
- Keep the name-intersection check. It fires before an instance exists, which the probe cannot.
- RULE #1 clean (ASCII hyphen only, no em dash, no en dash, no prose double-hyphen).
