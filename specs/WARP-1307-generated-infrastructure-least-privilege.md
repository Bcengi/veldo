---
schema: veldo.spec/v1
id: WARP-1307
title: Wildcard permissions and public-by-default exposure refuse in generated infrastructure -
  because `Action: *` and `0.0.0.0/0` are what the training data is full of
status: shipped
risk: standard - a pure checker over parsed infrastructure declarations. It is not low because it
  decides what reach a generated component gets, and permissive here is an open bucket shipped by a
  change about something else entirely.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0013
work: W7
depends_on: []
placement: [enforcement]
footprint:
  - ".veldo/generated_privilege.py"
  - "engine/.veldo/generated_privilege.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/01_warp_0101_reviewer_notes.py"
  - "specs/WARP-1307-generated-infrastructure-least-privilege.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      EVERY VIOLATION CLASS HAS A SEEDED NEGATIVE TEST AND A CONTROL BESIDE IT. Wildcard action,
      wildcard resource, wildcard principal, over-broad role, public ingress, public storage and a
      credential with no expiry each refuse when seeded, and the narrowed version of the SAME
      artifact is clean. Without the control a checker that refuses everything looks identical to
      one that works.
  - id: AC2
    text: >
      THE REFUSAL NAMES ITS OWN RULE AND THE NARROWER THING TO DO. "Least privilege violation" sends
      somebody to read source at the moment they are least able to. Every rule carries an `instead`
      line naming the specific alternative, and the report renders it.
  - id: AC3
    text: >
      IT READS PARSED STRUCTURE, NEVER TEXT. A regex over HCL or YAML matches a wildcard inside a
      comment and misses one built by string concatenation. The module takes parsed data; the caller
      parses. A selftest asserts a wildcard is found in structure that no textual scan of the source
      would have produced.
  - id: AC4
    text: >
      THE PER-STACK SLOT IS REAL AND COMPOSES. `Analyzer.extra()` is called and its findings appear
      alongside the reference rules, so a Terraform or Kubernetes analyser plugs in without
      modifying this module. Passing no analyser is the ordinary path and runs the reference rules
      alone.
  - id: AC5
    text: >
      THE BROAD-ROLE SET IS NAMED DATA, NOT A PATTERN. Adding a role to it is a decision somebody
      makes, not a regex that quietly widens over time. An ordinary narrow role binding passes, so
      the check is not simply refusing every role it sees.
required_evidence: [unit]
rollback: >
  Delete the module and its capability entry. It reads a dict and returns findings; no state, no
  gate wiring yet, no behaviour change.
---

## Outcome

Infrastructure a machine writes is held to least privilege before it merges.

## Why this class specifically, and why arguing with the model does not fix it

Every one of these violations exists in the training data in enormous quantity. `"Action": "*"` and
`0.0.0.0/0` are what tutorials use, because they make the example work without a section on IAM. An
agent reproducing the most common shape of a thing reproduces exactly the shape that got a thousand
blog posts past their authors' patience.

This is not a reasoning failure and it is not fixed by a better instruction. The next task starts
with a fresh context and the same training data. What holds is the check on the artifact.

## The refusal has to be actionable or it becomes a thing people route around

A gate that says "least privilege violation" sends an engineer to read the checker's source at the
worst possible moment. Every rule here carries the narrower alternative in the message: name the
four verbs you actually call, scope to the exact arn, front it with a signed url. That is the
difference between a refusal somebody fixes and one somebody adds an exception for.

## Structure, not text

The module takes parsed data and never a source string. A regex over HCL matches a wildcard in a
comment and misses one assembled by concatenation - which is the shape a generator produces most
often, because generators build strings.

## Proportionate, with a slot

This is a reference check, not a policy engine. A real per-stack analyser plugs in behind
`Analyzer`; what ships covers the classes that actually recur. A full IAM simulator would be the
wrong trade here: the check that runs on every change beats the check that is correct and unwired.
