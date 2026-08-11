---
schema: veldo.spec/v1
id: WARP-0303
title: DB/migration runner (reference) - B2 of PLAN-0003
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0003
work: B2
plan_revision: 2
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A generic DB/migration runner ships at
      engine/scripts/runners/db/veldo_db_runner.py. It reads a migration
      journey (JSON, an ordered list of migrations each with an id and up and
      down statement lists, an optional seed statement list, data invariants each
      a name plus a SQL query plus expected rows, and query-latency budgets each
      a name plus a SQL query plus max_seconds). Against a real database (the
      Python standard library sqlite3, so there is no external dependency) it
      snapshots the baseline schema, applies every migration's up in order,
      applies the seed, asserts each invariant, asserts each latency budget,
      then (unless disabled) applies every migration's down in reverse order and
      asserts the schema returns to the baseline. It exits 0 when everything
      holds and exits 1 with the first failing migration, invariant, budget, or
      un-reversed object named.
  - id: AC2
    text: The checks are real and fail loud. An invariant whose query result does
      not equal its expected rows fails with the observed rows named; a latency
      budget the query exceeds fails with the measured time; a down migration
      that does not restore the baseline schema fails naming the residual (or
      missing) schema object; and a SQL error in any statement is a named failure
      at that migration and statement, not a silent pass. Reversibility checking
      is on by default and can be turned off per journey (check_reversibility)
      for a deliberately irreversible data migration.
  - id: AC3
    text: A passing fixture and a deliberately-failing fixture ship under
      engine/scripts/runners/db/fixtures/. The passing fixture creates
      a schema over two reversible migrations, seeds rows, asserts row-count and
      distinctness invariants and a lookup latency budget, and reverses cleanly,
      so the runner exits 0. The failing fixture ships an asymmetric down (its up
      creates two tables but its down drops only one), so after the down a table
      remains, the reversibility check catches it, and the runner exits 1 naming
      the residual object.
  - id: AC4
    text: The runner's control logic is unit-tested in scripts/selftest.py with
      no external dependency - it drives the runner over both shipped fixtures
      against an in-memory sqlite database (pass to exit 0, fail to exit 1 with
      the residual object named), and the pure helpers are exercised directly for
      both outcomes (an invariant that matches and one that does not with the
      observed rows reported, a latency budget met and one exceeded, a schema
      diff that is empty and one that names a residual object, and a SQL error
      surfaced as a named failure). All prior selftest cases keep passing and the
      gate stays green.
  - id: AC5
    text: The runner is generic - zero company or product names in the runner,
      fixtures, wrapper, or README - and .veldo/capabilities.yaml (template and
      repository instance, kept byte-identical) declares it status reference (a
      shipped reference an adopting repo wires to its migration or data gate slot;
      the veldo repo does not run it), never mechanical. The docs-hygiene, secret,
      lint, and template-sync gates stay green.
required_evidence: [unit, operational]
rollback: git revert; B2 adds a new runner directory under engine, a
  selftest block, and an honest capabilities entry (template and instance) - no
  protected gate script or enforcer is touched, so reverting removes the
  reference artifact and its unit block with no effect on any running gate; the
  prior selftest cases are unchanged.
---

## Intent

PLAN-0003 (the batteries) ships a reference runner for every common product
surface. B2 is the database and migration surface. The outcome that should
become true is that a repository with a database can drop in a generic runner,
describe its migrations and the data invariants that must hold, and get proof
that a migration set applies, preserves those invariants, meets a query-latency
budget, and reverses cleanly. Migrations are among the highest-risk changes a
product makes (an asymmetric or lossy migration is discovered in production, not
at review), and they are invisible to a runner that only checks that the
application boots. This runner applies the migrations up and down against a real
database and asserts the schema and the data across the round trip.

## Context

B2 of PLAN-0003, feature F1 (surface runners), pulled against plan revision 2.
The runner follows the shipped runners' pattern: a generic reference artifact
under engine/scripts/runners/, a fixture PAIR (passing and
deliberately-failing), and a unit test that gate-tests the control logic with no
external service. Here the database is the Python standard library sqlite3, so
the runner drives a REAL database with zero install: the every-commit gate
applies the fixtures' migrations, runs their invariants and budgets, and checks
reversibility in an in-memory database. The distinctive assertion is
reversibility: a down migration that does not exactly reverse its up leaves the
schema drifted, and the runner names the residual (or missing) object rather
than reporting green, because an asymmetric down is a latent production incident.

## Out of scope

Cross-database dialects (the reference targets sqlite; an adopting repo points
the runner at its own database and migration format). Data-volume or concurrency
performance testing beyond a single query-latency budget. Online or zero-downtime
migration orchestration. Full data-migration verification beyond the declared
invariants. Wiring the veldo home repository's gate to this runner: the home repo
has no product database of its own, so the runner ships as a reference marked
status reference and is not run in the home gate.

## Notes

The run order is baseline snapshot, then every up in order, then the seed, then
invariants, then latency budgets, then (unless check_reversibility is false)
every down in reverse order and a final schema comparison to the baseline. The
schema snapshot reads sqlite_master and ignores auto-created indexes so an
invariant-preserving index does not read as drift. An invariant compares the
query's rows to expected rows exactly; a budget times a single query against
max_seconds. A deliberately irreversible data migration sets
check_reversibility to false and relies on invariants alone. The optional
[db_path] CLI argument (or the DB_PATH environment variable) runs against a file
database instead of the default in-memory one, so the same journey can target a
scratch copy of a real database unchanged.
