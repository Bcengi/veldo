---
schema: veldo.spec/v1
id: VELDO-0149
title: A project activates on any repository this domain adopted, by the owner's signed command or by his settled answer
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W109
plan_revision: 4
depends_on: [VELDO-0029, VELDO-0068, VELDO-0076]
placement: [contracts, engine, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_project*.py"
  - ".veldo/control_project*.py"
  - "packs/*/.veldo/control_project*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0149_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0149-project-activation-on-an-adopted-repository.md"
  - "specs/index.md"
  - "proof/VELDO-0149/*"
behavior_bearing: true
observability:
  logs: >
    Record each activation with its project, execution repository, the binding that adopted it and the
    path it came by (signed command or settled answer, naming the settlement), or its named refusal.
  metrics: >
    Count activations accepted and refused by path and by refusal.
  traces: >
    Join each activation to the repository binding it names and, when it came from an answer, to the
    request, presentation and settlement.
  error_taxonomy: >
    Distinguish a repository this domain never adopted, a missing bound field, a missing or unsettled
    answer, an answer by someone other than the current owner and a stale answer; none activates.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A project's execution repository is any repository adopted in this domain, and a repository
      no adoption in this domain recorded is refused. Set and completeness: Bind two repositories to the
      store through their VELDO-0029 enrollment bindings and activate one project on each with the
      owner's real signed command (VELDO-0076); each creates one active project bound to its repository.
      Name a repository that no binding in this domain records, and one bound in another domain, and
      require a named refusal with nothing written. Falsifier: Accept an execution repository that no
      adoption in this domain recorded; the adopted-repository check must fail.
    falsified_by: >
      Accept an execution repository that no adoption in this domain recorded; the adopted-repository
      check must fail.
  - id: AC2
    text: >
      Claim: Activation may be applied from the owner's settled answer to an activation request, binding
      the same fields as his signed command. Set and completeness: Present an activation request for a
      store-bound repository and settle the owner's answer through VELDO-0068; the settlement applies one
      activation that binds owner, charter, execution repository, authority policy and finite
      coordination budget, exactly as the signed command does. Omit each bound field from the request;
      apply an unsettled request, a settlement answered by a member who is not the project's current
      owner and an answer to a presentation that has since changed; each refuses by name with no active
      project. Falsifier: Apply an activation from a settlement answered by a member who is not the
      project's current owner; the owner-answer row must fail.
    falsified_by: >
      Apply an activation from a settlement answered by a member who is not the project's current owner;
      the owner-answer row must fail.
required_evidence: [unit, integration]
rollback: >
  Accept activation only by the owner's signed command on the store's one repository, as VELDO-0076 did;
  active projects, bindings and settlements are kept. No automatic rollback is authorized.
---

## Intent

The owner's projects live in several repositories, and he starts a project from chat by answering one
proposal. Activation must accept any repository this domain adopted and must be applicable from his
settled answer as well as from his signed command.

## Context

W109 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 4. Section 5 of the
approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner Telegram
29162) amends VELDO-0076 AC1: the execution repository is any repository adopted in this domain, and
activation may be applied from the owner's settled answer. VELDO-0076 has landed with its proof, so this
repository's convention puts that amendment in its own specification that depends on it, and VELDO-0076
keeps its landed text. Today VELDO-0076 accepts only the store's one repository and only the owner's
own signed key.

## Out of scope

Creating or adopting a repository (VELDO-0143); the new-project proposal and its answer (VELDO-0143);
several projects in one repository; any change to VELDO-0076's criteria.

## What the reviewer judges

- Normal use: the owner activates a project on any repository the store binds in this domain, with his
  signed command or by answering an activation request; exactly one active project results, bound as
  VELDO-0076 binds it.
- Threat model: an activation on a repository this domain never adopted, or adopted in another domain;
  an activation from an unsettled request, from a member who is not the current owner, or from an
  answer to a presentation that changed; an activation from an answer that binds less than the signed
  command would. The owner's account, the store and the signing edge are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); VELDO-0143's
  repository creation and adoption; recovery and restart (Release 2); forged rows in our own store and
  files planted in the installed directory.

## Notes

This concern's checks use a repository bound to the store through its enrollment binding and an
activation request settled through VELDO-0068, so they need nothing from VELDO-0143; VELDO-0143 then
applies its new-project settlement through this path. It is built with VELDO-0143 in the order of
section 12 of the design.

## History

2026-09-25: written for PLAN-0019 revision 4 from the approved operating-model design (Telegram 29162),
section 5(e), whose VELDO-0076 AC1 amendment is carried here whole because VELDO-0076 has landed; the
adopted repository and the answer path are one criterion each. Ready, as the amendment it carries was.
