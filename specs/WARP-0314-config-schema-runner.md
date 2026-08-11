---
schema: veldo.spec/v1
id: WARP-0314
title: Config-schema validation runner (reference) - B14 of PLAN-0003
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0003
work: B14
plan_revision: 2
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A config-schema validation runner ships at
      engine/scripts/runners/config/config_runner.py. It reads a
      fixture (a JSON object holding a schema and a list of labeled config
      samples), feeds every sample through the runner's own validator, and
      asserts that each sample labeled valid is ACCEPTED and each sample labeled
      invalid is REJECTED. The schema declares fields, each with a type and
      optional constraints (required, enum, pattern, min, max), and an optional
      allow_unknown flag. The runner exits 0 when every sample's accept or reject
      verdict matches its label and exits 1 naming the mismatch. Running the
      passing fixture exits 0; running the deliberately-failing fixture exits 1
      with the failing sample and the offending field named.
  - id: AC2
    text: Rejection is honest and names the offending field and reason. A missing
      required field, a type mismatch (JSON honest - a bool is not an integer, an
      integer satisfies a declared number, null is its own type), a value outside
      an enum, a string not matching a pattern, a numeric value outside its
      min/max, a string or array length outside its min/max, and an undeclared
      key when allow_unknown is false each produce a violation naming the field
      and the reason. An invalid sample may pin expect_field and expect_reason so
      the runner proves the config was rejected for the RIGHT reason, not merely
      rejected. A sample labeled valid that actually violates the schema is caught
      because its rejection mismatches its label - the exact defect the shipped
      failing fixture demonstrates.
  - id: AC3
    text: A malformed schema fails loud and an empty check is a fixture error. An
      unknown or missing type, a bad regex pattern, a min above a max, or an
      unknown field-spec key makes the schema malformed and the run exits 1
      naming the schema problem, so the runner never validates config against
      garbage and passes green. A fixture that declares no samples asserts
      nothing and is a fixture error, and a sample whose label is neither valid
      nor invalid is a fixture error.
  - id: AC4
    text: The control logic is unit-tested in scripts/selftest.py over its own
      schema and samples with NO external dependency, mirroring the other
      reference runners. The suite exercises accept, reject, and every constraint
      kind (required, type, enum, pattern, min and max as a numeric value and as
      a length, undeclared field), a malformed schema failing loud, an
      asserts-nothing fixture, and rejection for the wrong field; then the two
      shipped fixtures are driven end to end (pass -> exit 0, mislabeled -> exit 1
      with the offending field named). All prior selftest cases keep passing and
      the gate stays green.
  - id: AC5
    text: The runner is generic - zero company or product names in the runner,
      fixtures, wrapper, or README - and .veldo/capabilities.yaml (template and
      repository instance, kept byte-identical) declares it status reference (a
      shipped reference wired per repo to its own config schema and samples; the
      veldo home repo has no product config schema of its own to validate), never
      mechanical. The docs-hygiene, secret, lint, template-sync, and generated
      gates stay green.
required_evidence: [unit, operational]
rollback: git revert; B14 adds a new runner file, a fixture pair, a wrapper and a
  README under engine, a selftest block, and an honest capabilities
  entry (template and instance) - no protected gate script or enforcer is
  touched, so reverting removes the reference artifact and its unit block with no
  effect on any running gate; the prior selftest cases are unchanged.
---

## Intent

PLAN-0003 (the batteries) ships a reference runner for every common product
surface. B14 is the configuration surface. The outcome that should become true is
that a repository can prove its configuration validator actually rejects bad
config: it feeds valid and invalid config samples at the real validator and gets
proof that the valid ones are accepted and the invalid ones are rejected with an
error that names the offending field and the reason. A config validator earns
trust only by saying no to the config it should say no to; a suite whose samples
all pass proves nothing on its own, so the runner ships a deliberately-mislabeled
fixture that must fail.

## Context

B14 of PLAN-0003, feature F4 (contract and protocol surfaces), pulled against plan
revision 2, with no dependency. It follows the shipped runners' pattern: a generic
reference under engine/scripts/runners/, a fixture PAIR, a wrapper, a
README, and a unit block that gate-tests the control logic with the fixtures and
no live dependency. The schema is a compact, generic subset (fields with a type
and optional required, enum, pattern, and min/max constraints, plus an
allow_unknown flag) that covers the constraint kinds real config validators
express, and the validator is pure so the same runner drives an adopting repo's
own config loader once it imports validate_config or points the runner at its own
schema and samples.

## Out of scope

Cross-field and conditional constraints (field A required when field B is set),
defaulting and coercion, nested-object schemas beyond a single level of field
types, format vocabularies beyond regex patterns (date-time, email, uri), and
schema-language compatibility (JSON Schema, OpenAPI). The runner asserts a compact
declarative schema, which is enough to prove the accept/reject contract; an
adopting repo with a richer schema language wires its own validator behind the
same fixture-and-label harness.

## Notes

Why reference (not mechanical): the veldo home repo has no product config schema of
its own to validate, so the honest evidence is the fixture-driven control-logic
unit test, not a live-config run. required_evidence is [unit, operational]: the
unit block gate-tests the validator and both fixtures, and the operational
evidence is the wrapper driving both fixtures end to end (pass exits 0, the
mislabeled fixture exits 1 with the offending field named). capabilities.yaml
states status: reference, never mechanical.

The adversarial properties a reviewer should confirm by rerunning the selftest and
driving the fixtures: (1) every constraint kind, exercised one at a time, produces
a violation naming the offending field; (2) type matching is JSON honest, so a
bool is not accepted where an integer is declared and an integer is accepted where
a number is declared; (3) min/max bound the numeric value for a number and the
length for a string or array; (4) a malformed schema and a sample set of zero fail
loud rather than passing vacuously; (5) an invalid sample that pins expect_field is
only counted as matching when the rejection names that field, so a config rejected
for the wrong reason is still caught.
