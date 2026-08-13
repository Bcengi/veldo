---
schema: veldo.spec/v1
id: VELDO-0012
title: The behaviour floor contract - an existing codebase's current behaviour becomes a recorded
  artifact the machine may draft and may never rule on, where the ruling is representable ONLY as a
  human decision settled through the ticket channel and joined to the observation by a digest the
  validator recomputes, so the agent under the gate cannot write its own exemption
status: ready
risk: high - it is the root contract of the legacy on-ramp and it REGISTERS TWO NEW PROTECTED PATHS,
  which is itself a .veldo/policy.yaml edit and therefore a protected-path act needing a commit-bound
  approval. Two failure directions and both are serious: a floor that admits an inline ruling hands
  the agent being gated a place to write its own exemption, and a floor whose observation digest is a
  typed field hands it a pointer at somebody else's judgement. It is NOT critical because nothing here
  enforces anything - no change is refused because a pin is unruled, the artifact is inert data until
  a later item consumes it, and a repository with no .veldo/floors/ directory is byte-identically
  unaffected. It is not standard because the thing it protects is a record of what a named human said
  about behaviour, which is the only durable output of the whole on-ramp
owner: dmitry
human_approval: required
lane: standalone
depends_on: [WARP-0619]
placement: [contracts]
footprint:
  - ".veldo/behavior_floor.py"
  - "engine/.veldo/behavior_floor.py"
  - ".veldo/validate.py"
  - "engine/.veldo/validate.py"
  - ".veldo/validate_checks.py"
  - "engine/.veldo/validate_checks.py"
  # /veldo:init must LAY THE ORGAN DOWN, or a scaffolded repository raises FileNotFoundError
  # the first time run_all reaches the floor check. Derived, not remembered: the init scaffold
  # suite reads validate_checks for its literal loader paths and reds on an omission.
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  # The protected-path registration. policy.yaml is a DECLARED exception to the byte-identical
  # template sync (scripts/check_template_sync.sh:33), so this repository's protection and the
  # template an adopter installs are edited separately and are not compared.
  - ".veldo/policy.yaml"
  - "engine/.veldo/policy.yaml"
  - "scripts/suites/18_veldo_0012_behaviour_floor_contract.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0012-behaviour-floor-contract.md"
  - "specs/index.md"
protected_paths:
  - ".veldo/policy.yaml"
behavior_bearing: true
observability:
  logs: >
    A refusal names the floor file, the pin id, and WHICH cause fired, so an author fixes one pin
    rather than being told a floor is invalid. A stand-down prints one line naming which condition
    stood it down (no floors directory, or a floor with no pins), never a silent pass. The
    disposition read prints, per pin, one of ruled, unknown, or blocked WITH the reason, because
    "unknown" and "a human ruled and the channel could not carry which way" are different facts and
    a reader who cannot tell them apart will assume the first. AND THE READ NAMES WHAT IT WAS OVER,
    because a review measured the boundary in AC6 and this is the surface a person reads it on: one
    unconditional line (`DISPOSITION_READ_FROM`) says every disposition is resolved from records READ
    FROM THE WORKING TREE and that neither being tracked nor being covered by an approval is checked
    here, so `ruled incidental by dmitry` over four records nobody committed cannot read as a human
    ruling. It is the SAME string as the report dict's `read_from` key, recorded and reported from one
    place, because a fact held in a dict that nothing prints is a stand-down nobody sees.
  metrics: >
    The floor report carries pins, ruled, unknown and blocked counts, and it carries them BESIDE the
    scope block's enumerated-surface and unreachable-surface counts, so no coverage figure is
    quotable without the weakness that produced it. A floor never reports a percentage of an area.
  error_taxonomy: >
    Named, distinguishable causes rather than one undifferentiated refusal: FLOOR_UNREADABLE (an
    unparseable floor, and an entry in the floors directory the *.yaml rule does not claim),
    PIN_FIELD_MISSING, PIN_VOCAB_UNKNOWN, PIN_KEY_UNRECOGNIZED (the shape that would be an inline
    ruling), DIGEST_MISMATCH, DUPLICATE_PIN_ID, SCOPE_MISSING, and for the resolution states
    RULING_NOT_SETTLED (nothing settled carries this observation), RULING_NOT_CARRIED (a human
    settled a decision on this observation and no record it binds carries an option in the ruling
    vocabulary), RULING_BINDING_MISMATCH (a settlement carrying this observation's digest names an
    accepted request bound to a DIFFERENT artifact) and RULING_OPTION_OFF_RECORD (an option typed
    onto a settlement that no decided decision record corroborates, which the shipped receipt path
    cannot have written). Those four must never collapse into one name: nobody has ruled, the
    channel carried no option, the records disagree about what this settlement binds, and somebody
    typed a ruling into a settlement are four different facts, and the fix is a different person's
    job in each case.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Widen STATUSES in .veldo/behavior_floor.py from its single member unknown to also admit
      load_bearing, and the negative-fixture assertion that a pin declaring status load_bearing is
      refused by PIN_VOCAB_UNKNOWN must go red while the well-formed fixture must still be accepted,
      so the refusal is discriminating rather than a blanket rejection. ADDED AFTER REVIEW, for the
      record-shape half: replace the unclaimed-entry loop in check_floors_dir with a loop over an
      empty list, so an entry the *.yaml rule does not claim is skipped again, and the assertion that
      a floor written as contracts.yml and a subdirectory parked beside the floors are each refused
      by name must go red while the well-formed good.yaml in the same directory stays accepted.
    text: >
      THE ARTIFACT EXISTS AND THE ONLY STATUS A MACHINE MAY WRITE IS unknown. veldo.behavior_floor/v1
      is a per-area record under .veldo/floors/*.yaml holding pins and one scope block, validated
      structurally in the shape .veldo/arch.py and .veldo/decision.py already establish: required
      fields present, closed vocabularies honored, duplicate pin ids refused across the set (the rule
      .veldo/decision.py:239-241 already applies to decision ids), every internal reference resolving,
      and every entry in the floors directory CLAIMED: a file the *.yaml rule does not claim is
      refused by name rather than skipped, because a record no reader validates, counts or names is an
      input the machine reports as absent while a human reading a protected directory sees it. A pin carries id, surface, language, fidelity from the closed vocabulary {exact,
      proxy}, an observation block holding what was recorded and its digest, a reproduces reference
      naming the test IN THE ADOPTING REPOSITORY'S OWN SUITE that reproduces the observation, and a
      status whose vocabulary has exactly ONE member, unknown. The floor's scope block names the
      surfaces the drafting pass enumerated, the method it used, and the surfaces it COULD NOT REACH,
      and a floor with pins and no scope block is refused, because a floor that does not say what it
      did not look at is a coverage claim wearing an artifact's clothes.
  - id: AC2
    falsified_by: >
      Delete the recompute in .veldo/behavior_floor.py's pin validator so observation.digest is
      accepted as declared, and the assertion that a fixture whose observation.recorded was edited
      while its digest was left alone is refused by DIGEST_MISMATCH must go red; the positive control
      (an untouched fixture whose declared digest equals the recomputed one) must still pass, so the
      check is not simply refusing every pin.
    text: >
      THE OBSERVATION DIGEST IS DERIVED AND RE-VERIFIED, NEVER TYPED, AND THIS IS THE LOAD-BEARING
      PROPERTY OF THE WHOLE ITEM. The pin carries the recorded observation as data, and the validator
      RECOMPUTES the digest over one canonical serialization of it, the discipline
      .veldo/request.py:126-136 already uses for request_digest over the declared field tuple at
      .veldo/request.py:113-114 (a sorted-keys JSON blob and one hash, no second spelling). A pin
      whose declared digest does not equal the recomputed one refuses by name. The reason is
      adversarial rather than tidy: the digest is the ONLY join between a human's ruling and a
      behaviour (AC4), so a digest that is merely typed is a writable pointer at somebody else's
      judgement, and re-pointing it at a different observation is exactly how an agent grants itself
      a ruling it was never given. There is ONE canonicalization function and both the validator and
      the disposition read call it, so the two can never disagree about what the digest of an
      observation is.
  - id: AC3
    falsified_by: >
      Delete the unrecognized-key refusal from .veldo/behavior_floor.py's pin validator so unknown
      keys are ignored instead of refused, and the three assertions over a fixture planting
      decided_by, reason, and exempt_paths on one pin must go red (one per planted key). ADDED AFTER
      REVIEW, for the CALL SITE rather than the enumeration: delete the scope validation that runs
      before validate_floor's pins-less early return, and the assertion that a floor with NO pins
      whose scope block carries waived_paths, modules_not_pinned, ruled_by and disposition is refused
      once per key must go red, while the paired control (a pins-less floor with a legitimate scope
      block, and one with no scope block at all) must stay green. A closed enumeration behind a
      conditional call is the same defect one level down.
    text: >
      NO RULING AND NO EXEMPTION IS REPRESENTABLE IN THE FLOOR AT ALL. Every key set is CLOSED at
      every level of the artifact, and each level is checked WHENEVER THAT LEVEL IS PRESENT rather
      than only when the floor declares pins: any unrecognized key is refused by name, which makes
      decided_by, decided_at, reason, disposition, waived and exempt structurally unwriteable inside a
      floor rather than merely discouraged. And no key EXEMPTS a LOCATION: no path, glob, module or
      pattern scoped exemption is representable, because a path exemption exempts a location forever
      and the load-bearing behaviour that appears there next year is invisible, which is the mechanism
      specs/WARP-1310-honest-migration.md already refuses for secrets and this contract does not
      reintroduce under a friendlier name. The claim is deliberately narrower than "no key addresses a
      location": a pin's surface names a file and a function and area names an architecture area,
      because a floor has to say WHAT it pins, and a surface grants nothing on its own since a pin
      reads unknown until a human rules on its observation. The refusal is in the SCHEMA rather than
      in prose because prose instructions do not execute: the floor is a file the agent under the gate
      can open, so the only real answer is that there is nowhere in it for a ruling to go.
  - id: AC4
    falsified_by: >
      Have disposition_for fall back to the settlement record's own decided_by when the request
      lookup returns nothing, and the assertion that a settlement carrying the pin's digest with no
      accepted veldo.request/v1 record behind it leaves the pin unknown with RULING_NOT_SETTLED must
      go red. ADDED AFTER REVIEW, one per field that used to be trusted, because a review authored a
      complete ruling with NO human act. (a) Delete the comparison of the accepted request's own
      bound_artifact.digest against the recomputed observation digest, and the assertion that a
      settlement naming a REAL accepted request bound to a DIFFERENT artifact leaves the pin unknown
      with RULING_BINDING_MISMATCH must go red, while the paired control with the binding restored must
      still rule. (b) Make the resolver read the settlement's own `chosen` key at face value again, and
      the assertion that a settlement carrying an option no decided decision record corroborates
      BLOCKS with RULING_OPTION_OFF_RECORD must go red, while the corroborated case must still rule.
    text: >
      A RULING IS RESOLVED ONLY FROM A DECISION THAT WENT THROUGH THE TICKET CHANNEL, JOINED TO THE
      OBSERVATION BY DIGEST, AND THE FLOOR HOLDS NO POINTER TO IT. A read-only disposition_for(pin)
      resolves a ruling only when ALL of it holds, and EVERY FIELD IN IT IS COMPARED AGAINST ANOTHER
      RECORD rather than read at face value: a settlement record under .veldo/settlements/ (the records
      the PLAN-0016 receipt path writes, .veldo/request_reconcile.py:353-390) has schema
      veldo.decision/v1, decision "decided", and bound_digest EQUAL to the pin's recomputed
      observation digest; its request_id resolves to a veldo.request/v1 record whose touchpoint is
      decision_choice and whose status is accepted (.veldo/request.py:74-77, and the accepted-binding
      rule at .veldo/request.py:273-274); THAT RECORD'S OWN bound_artifact.digest is the same recomputed
      digest, which is free because the receipt path SETS the settlement's bound_digest from exactly
      that field (.veldo/request_reconcile.py:451), so the two disagreeing means the channel did not
      write this settlement from that request; and the ruling itself is the option A HUMAN CHOSE on the
      decision record that request binds by bound_artifact.ref, resolved the way
      .veldo/request.py:315-338 already resolves that same reference, required to be decided with an
      attributed decided_by and decided_at and to resolve BOTH to one of that record's own declared
      options (.veldo/decision.py:176-190) and to a member of the ruling vocabulary. An option typed
      onto the settlement is never a ruling: the shipped receipt path writes no option at all, so one
      sitting there was typed rather than settled, and it is accepted only as a corroboration of the
      decision record's option and BLOCKS by name otherwise. Anything else leaves the pin unknown or
      blocked. The floor carries NO reference to the ruling in either direction: the join is the digest
      and nothing else, so mutating the recorded observation changes the digest and the same settlement
      stops matching, which is C4 of the on-ramp design made mechanical. NEGATIVE CONTROL, and it is
      the leg that matters: a hand-written settlement carrying the right digest with no accepted
      request behind it rules nothing, and neither does one whose request was settled about a different
      artifact, so a forged file is not a ruling. WHAT THIS DOES NOT CLAIM, because a review proved the
      stronger claim false: every record in the chain is a file, so an actor able to write a consistent
      set of them across .veldo/floors/, .veldo/requests/, .veldo/decisions/ and .veldo/settlements/
      still authors a record set that reads as ruled. That is closed by AC6's protected-path rules plus
      the requirement that a consumer read a TRACKED record, and never by this reader.
  - id: AC5
    falsified_by: >
      Map the settlement word "decided" onto load_bearing when no chosen option is present, and the
      assertion that such a settlement resolves to blocked with RULING_NOT_CARRIED must go red; the
      companion assertion that a blocked pin is never reported as ruled and never silently reported
      as unknown must go red with it.
    text: >
      AN UNSUPPORTED RULING BLOCKS BY NAME AND IS NEVER DEFAULTED, WHICH IS WHAT THE SHIPPED CHANNEL
      CAN CARRY TODAY. The three rulings are a three-way choice, and the inbound edge derives only
      accept or reject from board states (.veldo/request_reconcile.py:104-107) and writes a settlement
      carrying decision, decided_by and bound_digest and NEVER the chosen option
      (.veldo/request_reconcile.py:247-256), while a decided veldo.decision/v1 requires a chosen
      option that resolves (.veldo/decision.py:183-190). So a settlement that matches a pin by digest
      and whose bound request carries no decided decision record with an option in the ruling
      vocabulary resolves to BLOCKED with the reason named: never to a ruling, never to a default, and
      never quietly back to unknown as if nobody had decided anything. An option typed onto the
      settlement itself does not lift the block either; it changes which name fires
      (RULING_OPTION_OFF_RECORD rather than RULING_NOT_CARRIED), because a record the shipped writer
      cannot have produced is a different problem from an incomplete channel. This is PLAN-0016's own
      rule applied rather than routed around (plans/PLAN-0016-human-decisions-through-jira.md:77-85: no
      decision is captured outside the channel and an unsupported kind BLOCKS with the reason named),
      and the settlement-side option carrier is a work item of that plan, named in the notes below and
      deliberately not invented here: rather than inventing a field, the resolver reads the option a
      human already chose on the decision record the request binds.
  - id: AC6
    falsified_by: >
      Remove the .veldo/floors/* entry from protected_paths in .veldo/policy.yaml and the assertion
      that policy_check.protected_patterns() returns a pattern matching .veldo/floors/example.yaml
      must go red; removing the .veldo/settlements/* entry reds the sibling assertion for a settlement
      path, and both are asserted through protected_patterns() rather than by reading the file, so the
      test pins the mechanism the gate uses and not a string in a document.
    text: >
      THE FLOOR AND THE SETTLED RULINGS SIT UNDER protected_paths, BECAUSE THE VALIDATOR IS NOT THE
      INTEGRITY. .veldo/policy.yaml protected_paths gains .veldo/floors/* and .veldo/settlements/* at
      floor high, which is the same registration and the same argument .veldo/policy.yaml:28-33
      records for .veldo/secret_inventory.json and which .veldo/secret_inventory.py:149-152 states
      plainly: the integrity of a disposition record is the integrity of a reviewed change plus the
      protected-path rules it sits under, and never its own validation. With the registration in
      place, COMMITTING a floor, a re-pointed observation or a settlement is a change that needs a
      commit-bound, path-scoped approval (.veldo/policy_check.py:439-447), so the agent being gated
      cannot LAND the record that exempts it. THE WORD IS committing BECAUSE A REVIEW MEASURED THE
      BOUNDARY AND THE EARLIER CLAIM OUTRAN IT: that enforcement iterates
      policy_check.changed_files(), which is `git diff --name-only <base>`
      (.veldo/policy_check.py:92-99) and therefore lists modifications to TRACKED files only, so an
      untracked record is matched by the pattern and never reaches the check. Driven in a throwaway
      repository, and the row is in the suite rather than in this sentence: a modified tracked floor,
      an untracked floor and an untracked settlement ALL match .veldo/floors/* or
      .veldo/settlements/*, and the enumeration contains only the first. That boundary is a property
      of the shipped enforcement rather than of this item - it applies identically to
      .veldo/secret_inventory.json, which this criterion cites as its precedent - and it is recorded
      here rather than patched because the enumeration belongs to .veldo/policy_check.py and every
      reader of the tracked set is one enumeration to build once. WHAT THIS ITEM THEREFORE OWES ITS
      CONSUMER, which is the half that matters for item 4 of the notes: a consumer that makes a
      precondition out of a disposition must require the record to be TRACKED and covered by an
      approval, never merely present on disk. Nothing here is such a consumer - no gate stage reads a
      disposition at all (AC7) - so nothing in this item depends on the gap, and the requirement is
      written where the consumer will read it. AND IT IS NAMED WHERE A PERSON READS IT, which is the
      half a second review found still implicit: the one organ here that a local reader runs is the
      floor report, and it printed `1 ruled ... ruled incidental by dmitry` over four records nobody
      committed beside its own sentence that nothing is read at face value. report_lines now carries
      one unconditional DISPOSITION_READ_FROM line saying the dispositions are resolved from records
      READ FROM THE WORKING TREE and that tracked-ness and approval are not checked here, and the same
      string is the report dict's read_from key (observability.logs). NOTHING REFUSES AN UNTRACKED
      FLOOR, deliberately: a floor is authored before it is committed, so a check that reddened on
      that would refuse the feature rather than gate it. Registering a new protected path is itself a
      policy.yaml edit, which is why this spec declares human_approval required and names
      .veldo/policy.yaml in its own protected_paths, exactly as
      specs/WARP-0720-approver-registry-declared.md does for the approver registry.
  - id: AC7
    falsified_by: >
      Delete the `if not d.is_dir()` stand-down at the top of check_floors_dir in
      .veldo/behavior_floor.py, and the assertion that an absent floors directory RECORDS a
      stand-down naming its reason must go red, because the deletion removes the only call that
      records one. CORRECTED AFTER MEASUREMENT, and the original is kept here because the mistake is
      the instructive part: this field used to name the byte-identity assertion over run_all's
      output, and that assertion CANNOT see this mutation - on CPython
      `Path("missing").glob("*.yaml")` yields nothing and raises nothing, so with the guard gone the
      function still returns 0 and still prints nothing. A declared falsification naming an
      assertion that is structurally incapable of failing is worse than none, because it reads as
      proof that the leg is defended. The second leg (no gate stage refuses on an unruled pin) is
      asserted by the derived-domain scan described in the text.
    text: >
      ADOPTION SAFE, AND IT ENFORCES NOTHING. An absent .veldo/floors/ directory stands the whole
      check down and returns clean, exactly as .veldo/decision.py:219-227 does for decision records
      and as .veldo/validate_checks.py:400-411 wraps it, and the new check registers beside
      check_decisions in run_all (.veldo/validate.py:829-834) so there is no second catalog. NO
      CHANGE IS REFUSED BECAUSE A PIN IS unknown OR blocked: the precondition at ready and at claim is
      a later item, and this one is asserted to be outside the enforcement path over a DERIVED domain
      rather than a typed list, in the shape specs/WARP-1409-cost-to-change-per-area.md's AC6 uses:
      parse scripts/verify.sh for every catalog item declared required and every direct invocation in
      the always-run body, close that set over what each member loads, and require that no member
      refuses on a disposition state. The moment a floor exists it fails closed on anything malformed,
      which is the other half of the same posture.
required_evidence: [unit]
rollback: >
  Delete .veldo/behavior_floor.py and its engine twin, remove the one registration line in
  validate.run_all and its wrapper in validate_checks.py, remove the suite file and its manifest
  entry, and regenerate scripts/suites/requires.json and specs/index.md. Nothing reads the module, no
  gate stage consumes its output, and it writes no state. Reverting the two protected_paths entries is
  itself a protected-path act and needs its own approval, which is the correct asymmetry: protection
  is cheap to add and deliberately expensive to remove. Any floor already written stays as inert data
  that no reader consults, and a repository with no .veldo/floors/ directory is unaffected either way.
---

# The behaviour floor contract

## Intent

Every real adopter has an existing codebase and the shipped method has no answer for one. The pilot
path at `docs/setup.md:1079-1091` runs repository clarity, contracts and specifications, the canonical
gate, first full changes, independent review, merge policy: ten days, and not one of them pins what the
code currently does. The adoption sequence in `docs/method.md:1312-1359` has the same six phases and
the same hole. So the first instruction an adopter with a ten year old monolith receives is to write
specifications and turn on a gate against a codebase whose behaviour nobody has written down.

The book promises otherwise, in plain words. `ch14-adoption.md:24-33` of the manuscript at
`/home/dmitry/projects/books/sdlc-for-ai-age/manuscript/` promises that when a change is coming to
some part of the estate, the machine drafts characterization tests that pin what the code DOES today,
a human confirms that what-is is what-should-be or files the difference as a finding, and the spec for
the change is written against that pinned floor. Lines 35-41 promise the architecture contract is
harvested from the code as found; lines 43-50 promise a gate that starts permissive and ratchets while
everything new meets the full standard from the first commit.

None of it exists here, verified by grep across the tree excluding `.git`: `characteriz` and
`characteris` appear only in unrelated prose (`CODE_OF_CONDUCT.md:15`, `proof/WARP-1108/verdict.json:67`,
`.veldo/untrusted_input.py:98` and its engine twin, `docs/research/11-briefing-failure-modes-of-low-process-ai.md:21`);
`brownfield` appears only in `docs/landscape.md:72` and two research briefings, always describing a
competing tool and never as a practice of this method; and `behaviour floor`, `golden master`,
`approval test` and `pin current` return nothing at all.

This item is the ROOT of the on-ramp and only the root: the artifact, its refusals, and the channel a
ruling must arrive through. It draws no conclusions, refuses no change, and consumes nobody's budget.

## Context

### The hard part, stated rather than routed around

A characterization test pins current behaviour INCLUDING current bugs. Pinning is therefore not the
deliverable. The deliverable is a record of which pinned behaviour is load bearing, which is merely
present, and which is a defect somebody has now seen: who said so, on what date, about which exact
observation. `docs/method.md` reserves that judgement for humans, and it is the right reservation,
because the question is not what the code does (a machine reads that better than a person) but whether
what it does is what it should do.

Three answers are available and two are wrong. Having a human review every pin is a survey of an
estate, months of attention spent before anything ships and stale before it finishes. Letting the
machine classify puts a GUESS in the record, and a record that remembers a guess is worse than no
record because the guess is now authoritative. The third wrong answer, which a hurried implementation
reaches for, is a path scoped exemption: mark this legacy directory incidental and move on. AC3
forbids all three in the schema rather than in prose.

What is left is the design this contract implements: the machine records observations and cannot rule;
the ruling is a human decision that arrives through the one channel this repository already has for
human decisions; and the ruling binds to the OBSERVATION rather than to a location, so a human's
judgement can never silently transfer to a behaviour they did not see.

### Why the ruling goes through PLAN-0016 and not through a new field

`plans/PLAN-0016-human-decisions-through-jira.md` is approved, at `risk: critical`, and its O6
(lines 77-85) says no decision is ever captured outside the ticket channel, there is no manual
hand-advancement of a record, and an unsupported decision kind BLOCKS rather than bypassing. An
on-ramp that invented its own ruling field would be a second decision surface with no attributed
actor, no binding to what was ruled on, and no receipt, in the exact place where the whole capability's
value lives. So there is no ruling field. The ruling is a `decision_choice` touchpoint
(`.veldo/request.py:74-77`) whose settlement the receipt path writes to `.veldo/settlements/`
(`.veldo/request_reconcile.py:353-390`), and the pin is joined to it by the digest of the observation.

That reuse buys three properties for free rather than by argument: the actor is derived from the
attributed changelog and never from the record (`.veldo/request_reconcile.py:31-39`), the settlement is
written once through an append-only compare-and-swap receipt (`:41-44`), and the authorization,
separation of duties and quorum come from repository policy through the shipped engine. It also
answers who may rule, which the design draft answered as "anybody with commit access, attributably":
whoever the approver registry names for the tier, under the separation rules, per
`specs/WARP-0720-approver-registry-declared.md`.

### What the channel cannot carry yet, and why that is a block rather than a gap

A pin ruling is a three-way choice, and the inbound edge derives only accept or reject from board
states (`.veldo/request_reconcile.py:104-107`). Its settlement record carries `decision`, `decided_by`
and `bound_digest` and never the CHOSEN OPTION (`:247-256`), while a decided `veldo.decision/v1`
requires a chosen option that resolves (`.veldo/decision.py:183-190`). So the SETTLEMENT cannot say
which way a human ruled. AC5 makes that state explicit and named (`RULING_NOT_CARRIED`) instead of
guessing, and the settlement-side option carrier is work for PLAN-0016, which owns that edge.

Where the option DOES live today, and why reading it there is not an invention: a `decision_choice`
request binds a `veldo.decision/v1` DECISION RECORD by `bound_artifact.ref`, and that record carries
the option a human chose among its own declared options, validated by the shipped decision organ and
already resolved through that exact reference by `.veldo/request.py:315-338` to derive the request's
tier. So AC4 reads the ruling from the record the touchpoint is ABOUT, and never from a key typed onto
a settlement. Until the settlement-side carrier lands, a pin reads `ruled` only when such a record
exists, decided and attributed, and otherwise reads unknown or blocked, which is the honest reading and
is exactly what PLAN-0016's own no-bypass rule prescribes. A REVIEW CORRECTED AN EARLIER CLAIM HERE:
this paragraph used to say every pin reads unknown or blocked until the carrier lands, while the
resolver accepted a top-level `chosen` key on a settlement at face value, so the only reachable route
to `ruled` was a record no shipped writer can produce. That route is now refused by name.

### The language scope, declared rather than implied

The shipped shape analyzers are Python only: `.veldo/shape_gate.py:175-182` filters the changed set to
paths ending `.py` before any analyzer sees them. So a floor over a Java, Kotlin, Rust or SQL surface
gets no help from the shipped analyzers, its `reproduces` reference points at a test in the adopting
repository's own framework, and its `language` field plus the scope block's unreachable list is how the
artifact says so. Nothing in this item claims a floor over a surface it cannot enumerate.

## Out of scope

- THE DRAFTING PASS. Enumerating a footprint's surfaces and recording what each does today is the next
  item. This one validates an artifact and reads it; it writes no pins.
- THE RULING MECHANICS. What `load_bearing`, `incidental` and `defect` each DO mechanically (a guard a
  change must name, a tripwire whose alteration appends an event with both digests, a defect held green
  with a drafted finding) is a later item and is blocked on the option carrier above.
- THE PRECONDITION AT ready AND AT claim. Refusing a spec whose footprint intersects an unruled pin is
  a later item. AC7 asserts this item is outside the enforcement path.
- ANY CHANGE TO THE ARCHITECTURE CONTRACT, THE GATE, THE REVIEW, THE POLICY MACHINERY BEYOND THE TWO
  protected_paths ENTRIES, THE RESTORATION LOOP OR THE ESTIMATOR. Every one of them is extended by
  later items through its own established pattern, and none is redesigned.
- THE HARVESTED ARCHITECTURE BASELINE and the observe/enforce ratchet. Independent lanes with their own
  roots; neither needs the floor and the floor does not need them.
- REVERSE SPECIFYING AN ESTATE. Nothing here writes specifications for code nobody is changing. A
  project to specify the whole system is the big bang rewrite in a documentation costume.
- ANY LIVE MIGRATION. This machinery is proven against fixtures. Running it over a real monolith is a
  separate, per repository, human owned act, and its cost is real.
- A RUNWAY ESTIMATE. Cut, not deferred: see the notes.

## Notes

### What follows this item, in order

1. THE DRAFTING PASS. Given a footprint, enumerate the surfaces, record what each does today, emit a
   floor whose every pin is unknown, and make the scope declaration the deliverable it is: which
   surfaces were enumerated, by what method, and which the pass could not reach, in the artifact rather
   than in a log line. Blocked on nothing in this list.
2. THE OPTION CARRIER, a PLAN-0016 work item and not an on-ramp one. The inbound edge learns to carry
   WHICH option an attributed human chose, so a three-way ruling can settle at all. Everything below
   is blocked on it.
3. THE RULING MECHANICS, three rulings doing three different mechanical things, including the
   supersession chain from old digest to new after a defect is fixed.
4. THE PRECONDITION at ready and at claim, refusing a spec whose declared footprint intersects a pin no
   human has ruled on, scoped to the change and never a corpus sweep, in the shape
   `.veldo/shape_gate.py:26-36` already uses for the size budget.
5. INHERITED TEST STANDING, a floor pin as a legitimate `required_evidence` kind, with an unmapped
   inherited test REPORTED as unattributed and never refused, because deleting a test nobody can
   explain is how coverage dies.
6. THE HARVESTED ARCHITECTURE BASELINE, an independent lane: propose a `veldo.arch/v1` contract from the
   code as found, split per rule by evidence into enforceable and direction, one restoration intent per
   gap, emitted as a draft with no approver.
7. THE RATCHET, also independent: an `observe` posture in the gate catalog on a dated declaration with a
   named decider, plus the teeth, where the inherited violation set is recorded as a set of violation
   IDENTITIES rather than a count so remeasuring against a dirtier tree cannot enlarge it.

### The runway estimate is CUT, not deferred

The design draft carried a per area on-ramp cost estimate. It is removed, because the number it would
produce is one this repository has already measured as unknowable from inside a repository:
`.veldo/cost_to_change.py:30-34` records that not one of 904 events carries `tokens`, `cost_usd` or
`human_minutes`, and `specs/WARP-1409-cost-to-change-per-area.md` reports 0 of 174 records carrying any
spend at all with `usable_as_cost_ground_truth` false. An on-ramp estimate built on that corpus would
be a confident zero with a basis label, which is the one output this repository refuses to print. If
the runway is wanted, the honest route is an emitter that records spend first, and then the existing
estimate machinery, with no second cost model.

### The decisions this item resolves, and by what argument

- WHO MAY RULE. Not "anybody with commit access, attributably". Whoever the approver registry names for
  the tier, under the shipped separation of duties, through the ticket channel. The draft's answer
  invented a fourth decision surface in a plan that forbids one.
- WHERE A PIN'S OBSERVATION LIVES. The reproducing test lives in the ADOPTING REPOSITORY'S OWN SUITE in
  its own framework and the floor holds a reference to it plus the digest of the observation it asserts.
  A method that generates a parallel test system will be deleted by the first engineer who meets it.
  STATED HONESTLY AFTER A REVIEW MEASURED IT: the digest covers `surface` and the recorded observation
  ONLY (`OBSERVATION_DIGEST_FIELDS`), so it does NOT make the `reproduces` reference load bearing - a
  pin can point at any test, and re-pointing it does not change the digest or disturb a granted ruling.
  What the digest makes immovable is the OBSERVATION a human ruled on. Whether `reproduces` and
  `fidelity` belong inside the digest is a real question for the item that consumes them, and this
  contract does not pretend they are covered. Reversible: choosing the other option changes the shape of
  the `reproduces` field and nothing else in this contract.
- HOW WIDE THE JOIN IS, NAMED RATHER THAN LEFT TO THE READER, because a review priced it. The digest is
  sha256 TRUNCATED TO 16 HEX CHARACTERS, which is 64 bits, and that is this repository's convention for
  every digest of this kind rather than a choice made here: `.veldo/request.py`'s `request_digest`
  truncates identically, which the suite asserts as an EQUALITY of the two widths so widening one alone
  reds the row. What 64 bits buys and does not buy: moving a ruling onto an EXISTING digest is a second
  preimage at 2^64 and is not a practical concern, while two observations chosen AT DRAFTING TIME to
  collide is a birthday search near 2^32 over short inputs, which is ordinary CPU time - and a drafting
  pass authors both pins. So no assertion in this item says a ruling "can never" transfer between two
  pins; it says the observations differ and the digests differ with them, up to that bound. Widening
  the truncation is a repository-wide convention change and is NOT made here, because two widths for
  one convention is worse than one narrow one.

### The decisions left OPEN, and what each blocks

- THE OPTION CARRIER ON THE INBOUND EDGE. Blocks every real ruling and therefore items 3, 4 and 5 above.
  It does NOT block this item: AC5 exists precisely so the incomplete channel is a named state rather
  than an invitation to invent one. It is PLAN-0016's decision because it is PLAN-0016's edge.
- PROXY PINS. Much of a real estate cannot be pinned exactly (a timestamp, an ordering, a production
  only path). The `fidelity` vocabulary {exact, proxy} makes BOTH answers representable, so this
  contract is stable either way; what stays open is whether the drafting pass may emit a proxy pin at
  all, and whether a proxy pin may ever be the load-bearing guard that blocks a change. The recommended
  answer is that it may be a tripwire and never a guard, because a flaky guard is a gate somebody
  switches off. AND THE ITEM THAT DECIDES IT INHERITS A MEASURED FACT ABOUT THE JOIN, stated here
  because a review measured it and it changes the shape of that decision: `fidelity` is OUTSIDE
  `OBSERVATION_DIGEST_FIELDS`, so a pin ruled `load_bearing` while its fidelity read `exact` is STILL
  ruled after the machine flips that field to `proxy` - the digest does not move and the same
  settlement still matches. Driven in the suite rather than argued here. So whoever consumes
  `fidelity` is consuming a field the human's ruling never covered, and the two available answers are
  to put it inside the digest (which re-points every existing ruling, since the digest changes) or to
  require the consumer to re-ask. Blocks the drafting pass and the mechanics, not this item.
- WHETHER THE PRECONDITION IS MANDATORY once a repository declares the on-ramp active, or advisory
  forever. Blocks item 4 and the documents that describe it.
- WHETHER `.veldo/settlements/*` PROTECTION BELONGS HERE OR TO PLAN-0016. It is claimed here because the
  floor is the first reader that treats a settlement as an exemption, and it is one line to move.

### Sizing, and where the seam is if this must be split

Seven criteria, one concern each. If the founder wants it smaller, the seam is between AC3 and AC4:
AC1 through AC3 are the ARTIFACT and its refusals and can land alone, and AC4 through AC5 are the
RESOLVER, which is meaningless without the artifact and touches no other file. AC6 must land with
whichever half creates `.veldo/floors/`, because an unprotected floor is the defect this item exists to
close. AC7 belongs to both halves and is cheap to assert twice.

RULE #1 clean (ASCII hyphen only, no em dash, no en dash, no prose double hyphen).
