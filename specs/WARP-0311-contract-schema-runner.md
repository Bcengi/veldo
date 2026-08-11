---
schema: veldo.spec/v1
id: WARP-0311
title: Contract/schema drift runner (reference) - B11 of PLAN-0003
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0003
work: B11
plan_revision: 2
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A contract/schema drift runner ships at
      engine/scripts/runners/contract/veldo_contract_runner.py. It reads
      a contract (a name, a version, a strict flag, and a golden schema mapping
      dotted field paths to JSON type names) and captures a real payload through
      a PRODUCER seam - a callable returning the payload, defaulting to the
      contract's captured fixture block so the runner is replayable with no live
      producer. It derives the captured payload's actual schema (dotted paths to
      types, recursing into objects and into list element shapes), diffs it
      against the golden, and exits 0 when there is no breaking drift and exits 1
      with each drift named (path and kind). An adopting repo passes
      producer=its own callable (which calls its real service) unchanged.
  - id: AC2
    text: Drift is classified honestly. A field in the golden but absent from the
      captured payload is a removed drift (breaking); a field whose captured type
      differs from the golden type is a type_changed drift (breaking); a field in
      the captured payload but not in the golden is an added drift. Removed and
      type_changed always fail. An added field fails only when the contract is
      strict (an additive change is nonbreaking for a tolerant reader but a
      contract that pins its surface catches it); a non-strict contract tolerates
      additions and still fails on any removal or type change. Type derivation is
      JSON-honest: a bool is not an integer or a number, an integer is a number,
      null is its own type, and objects and arrays are distinguished; list
      element shapes are derived under a path[] segment so a typed field inside a
      list is checked.
  - id: AC3
    text: The contract is versioned and the check cannot pass vacuously. The
      result records the contract name and version, so a captured payload is
      always graded against a pinned golden version and a deliberate breaking
      change is a new golden version rather than silent drift. A contract with an
      empty golden schema asserts nothing and is a contract error (a check that
      asserts nothing is not proof), failed loud. A producer that raises is a
      named capture error, not a silent pass.
  - id: AC4
    text: The control logic is unit-tested in scripts/selftest.py with a captured
      fixture payload and NO live producer, mirroring the other reference
      runners. Schema derivation is exercised for nested objects, list element
      shapes, and every JSON type (including bool-is-not-integer and
      integer-is-a-number); the diff is exercised for a clean match, a removed
      field, a type change, and an addition under both strict and non-strict; an
      empty golden schema is a contract error. Two shipped fixtures (a payload
      that matches its golden and a payload that has drifted) are driven end to
      end (pass -> exit 0, drift -> exit 1 with the drift named). All prior
      selftest cases keep passing and the gate stays green.
  - id: AC5
    text: The runner is generic - zero company or product names in the runner,
      fixtures, wrapper, or README - and .veldo/capabilities.yaml (template and
      repository instance, kept byte-identical) declares it status reference (a
      shipped reference wired per repo to its own producer and golden contracts;
      the veldo home repo ships no versioned payload contract of its own), never
      mechanical. The docs-hygiene, secret, lint, and template-sync gates stay
      green.
required_evidence: [unit]
rollback: git revert; B11 adds a new runner file, a fixture pair, a wrapper and a
  README under engine, a selftest block, and an honest capabilities
  entry (template and instance) - no protected gate script or enforcer is
  touched, so reverting removes the reference artifact and its unit block with no
  effect on any running gate; the prior selftest cases are unchanged.
---

## Intent

PLAN-0003 (the batteries) ships a reference runner for every common product
surface. B11 is the contract/schema drift surface. The outcome that should
become true is that a repository can freeze the shape of a payload its service
produces (or a consumer depends on) as a VERSIONED GOLDEN contract, capture a
real payload, and get proof that the payload still conforms - and, crucially, a
signal when it has DRIFTED: a field quietly removed, a type quietly changed, or a
field quietly added. A happy-path check that a specific field is present misses
the field that vanished and the field that changed type two releases ago. This
runner compares the WHOLE derived shape against the frozen golden, so drift is
caught wherever it happens, and it is versioned so a deliberate breaking change
is a new golden version rather than a silent surprise to a consumer.

## Context

B11 of PLAN-0003, feature F4 (contract and protocol surfaces), pulled against
plan revision 2, with no dependency. It follows the shipped runners' pattern: a
generic reference under engine/scripts/runners/, a fixture PAIR, a
wrapper, a README, and a unit block that gate-tests the control logic with a
captured fixture payload and no live producer.

How it differs from the integration/contract runner (WARP-0307): that runner
drives a live endpoint and asserts a hand-written per-interaction contract (a
listed set of required fields, types, and forbidden fields). This runner is a
GOLDEN SNAPSHOT contract: the full expected shape is a stored, versioned golden,
and the runner detects ANY drift from it - including removals and additions that
a hand-written required-field list never enumerated. The two are complementary:
one asserts an explicit contract at a live boundary, the other freezes and
diffs the whole shape over time.

## Out of scope

Value-level assertions (this runner checks the SHAPE - field presence and types -
not that a price equals 9.99; the LLM/eval and integration runners cover value
and behavioral assertions). Automatic golden capture or golden updating (an
adopting repo captures and versions its golden deliberately; the runner reads a
frozen golden, it does not rewrite it). JSON Schema or protobuf format
compatibility (the golden here is a simple derived path-to-type map, framework
neutral). Driving a live producer in the home gate, because the veldo repo ships
no versioned payload contract of its own; the honest evidence is the
captured-fixture control-logic test.

## Notes

Why reference (not mechanical): the veldo home repo has no versioned payload
contract of its own to freeze and diff, so the honest evidence is the
captured-fixture unit tests, not a live-producer run. required_evidence is
[unit]. The producer is a seam so an adopting repo swaps in its real service
call. capabilities.yaml states status: reference, never mechanical.

The adversarial properties a reviewer should confirm by rerunning the selftest
and driving the fixtures: (1) schema derivation is JSON-honest (a bool is not an
integer, an integer is a number, null is its own type, list element shapes are
derived); (2) a removed golden field and a type change each fail as breaking
drift, named with the path; (3) an added field fails under strict and is
tolerated under non-strict, while removals and type changes fail regardless of
strict; (4) an empty golden schema is a contract error, not a vacuous pass; (5)
the version is recorded so grading is always against a pinned golden.
