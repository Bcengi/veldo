#!/usr/bin/env python3
"""VELDO DB/migration runner (reference).

Applies a set of migrations UP and DOWN against a REAL database and asserts the
schema and the data across the round trip. Migrations are among the highest-risk
changes a product makes: an asymmetric down (one that does not exactly reverse
its up) or a lossy up is normally discovered in production, not at review. This
runner catches that at the gate. It drives the Python standard library's sqlite3
so the reference runs with no external dependency; an adopting repo points it at
its own database and migration format.

  veldo_db_runner.py <journey.json> [db_path]

The optional [db_path] (or the DB_PATH environment variable) runs against a file
database instead of the default in-memory one, so the same journey can target a
scratch copy of a real database unchanged.

Journey format (JSON):
  {
    "name": "users schema v2",
    "check_reversibility": true,
    "migrations": [
      {"id": "0001_users",
       "up":   ["CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL)"],
       "down": ["DROP TABLE users"]},
      {"id": "0002_email_index",
       "up":   ["CREATE UNIQUE INDEX ux_users_email ON users(email)"],
       "down": ["DROP INDEX ux_users_email"]}
    ],
    "seed": ["INSERT INTO users (id, email) VALUES (1, 'a@example.test')"],
    "invariants": [
      {"name": "one user seeded", "query": "SELECT count(*) FROM users",
       "expect_rows": [[1]]}
    ],
    "budgets": [
      {"name": "lookup by id", "query": "SELECT email FROM users WHERE id = 1",
       "max_seconds": 0.5}
    ]
  }

Run order: snapshot the baseline schema, apply every migration's up in order,
apply the seed, assert every invariant, assert every latency budget, then
(unless check_reversibility is false) apply every migration's down in reverse
order and assert the schema returns to the baseline.

  invariant   query result must equal expect_rows exactly (rows as lists)
  budget      query must complete within max_seconds
  reversibility  after all downs, the schema (sqlite_master, minus auto indexes)
                 must match the pre-migration baseline

Exit 0 = everything held. Exit 1 = the first failing migration, invariant,
budget, or un-reversed object is named. A SQL error is a named failure, never a
silent pass.
"""
import json
import os
import sqlite3
import sys
import time
from pathlib import Path


def snapshot_schema(conn):
    """Return the schema as a sorted list of (type, name, sql), ignoring
    sqlite's auto-created indexes (an invariant-preserving index is not drift).
    """
    rows = conn.execute(
        "SELECT type, name, sql FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_autoindex_%' ORDER BY type, name"
    ).fetchall()
    return [(t, n, s) for (t, n, s) in rows]


def schema_diff(baseline, after):
    """Return a list of human-readable differences between two schema
    snapshots. Empty means the schemas are identical (a clean reversal)."""
    b = {(t, n): s for (t, n, s) in baseline}
    a = {(t, n): s for (t, n, s) in after}
    diffs = []
    for key in sorted(a.keys() - b.keys()):
        diffs.append(f"residual {key[0]} {key[1]!r} remains after down")
    for key in sorted(b.keys() - a.keys()):
        diffs.append(f"{key[0]} {key[1]!r} was not restored by down")
    for key in sorted(a.keys() & b.keys()):
        if a[key] != b[key]:
            diffs.append(f"{key[0]} {key[1]!r} definition changed after round trip")
    return diffs


def check_invariant(conn, inv):
    """Run an invariant query and compare its rows to expect_rows exactly.
    Returns a list of failure strings; empty means the invariant held."""
    query = inv.get("query")
    expect = inv.get("expect_rows")
    if not query or expect is None:
        return [f"invariant {inv.get('name')!r}: malformed, declare both a query and "
                f"expect_rows (an invariant that asserts nothing is not proof)"]
    try:
        got = [list(r) for r in conn.execute(query).fetchall()]
    except Exception as e:
        return [f"invariant {inv.get('name')!r}: SQL error ({e})"]
    if got != expect:
        return [f"invariant {inv.get('name')!r}: expected rows {expect!r}, got {got!r}"]
    return []


def check_budget(conn, budget):
    """Time a single query against max_seconds. Returns a list of failure
    strings; empty means the query completed within budget."""
    query = budget.get("query")
    limit = budget.get("max_seconds")
    if not query or limit is None:
        return [f"budget {budget.get('name')!r}: malformed, declare both a query and "
                f"max_seconds (a budget that asserts nothing is not proof)"]
    start = time.monotonic()
    try:
        conn.execute(query).fetchall()
    except Exception as e:
        return [f"budget {budget.get('name')!r}: SQL error ({e})"]
    elapsed = time.monotonic() - start
    if elapsed > limit:
        return [f"budget {budget.get('name')!r}: {elapsed:.4f}s exceeds budget {limit}s"]
    return []


def _apply(conn, statements, where):
    """Execute a list of SQL statements. Returns a failure list (fail loud on
    the first SQL error, naming where it happened)."""
    for i, stmt in enumerate(statements or []):
        try:
            conn.execute(stmt)
        except Exception as e:
            return [f"{where}: statement {i} failed ({e}): {stmt}"]
    return []


def run(journey, db_path=None):
    """Apply the migration journey and return a machine-readable result.

    Stops at the first failure. Uses an in-memory sqlite database unless db_path
    (or DB_PATH) points at a file, so the same journey can target a scratch copy
    of a real database unchanged.
    """
    result = {"journey": journey.get("name"), "passed": True,
              "steps": [], "error": None}
    target = db_path or ":memory:"
    conn = sqlite3.connect(target)
    try:
        migrations = journey.get("migrations", [])

        def fail(step, failures):
            result["steps"].append({"step": step, "ok": False, "failures": failures})
            result["passed"] = False

        baseline = snapshot_schema(conn)

        for m in migrations:
            f = _apply(conn, m.get("up"), f"up {m.get('id')}")
            if f:
                fail(f"up {m.get('id')}", f)
                return result
            result["steps"].append({"step": f"up {m.get('id')}", "ok": True})

        f = _apply(conn, journey.get("seed"), "seed")
        if f:
            fail("seed", f)
            return result

        for inv in journey.get("invariants", []):
            f = check_invariant(conn, inv)
            if f:
                fail(f"invariant {inv.get('name')}", f)
                return result
            result["steps"].append({"step": f"invariant {inv.get('name')}", "ok": True})

        for budget in journey.get("budgets", []):
            f = check_budget(conn, budget)
            if f:
                fail(f"budget {budget.get('name')}", f)
                return result
            result["steps"].append({"step": f"budget {budget.get('name')}", "ok": True})

        if journey.get("check_reversibility", True):
            for m in reversed(migrations):
                f = _apply(conn, m.get("down"), f"down {m.get('id')}")
                if f:
                    fail(f"down {m.get('id')}", f)
                    return result
                result["steps"].append({"step": f"down {m.get('id')}", "ok": True})
            diffs = schema_diff(baseline, snapshot_schema(conn))
            if diffs:
                fail("reversibility", [f"down did not restore the baseline schema: {d}" for d in diffs])
                return result
            result["steps"].append({"step": "reversibility", "ok": True})
    finally:
        conn.close()
    return result


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    journey = json.loads(Path(sys.argv[1]).read_text())
    db_path = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("DB_PATH")
    result = run(journey, db_path=db_path)
    for s in result["steps"]:
        if s["ok"]:
            print(f"PASS {s['step']}")
        else:
            print(f"FAIL {s['step']}")
            for f in s["failures"]:
                print(f"     - {f}")
    if result["error"]:
        print(f"ERROR: {result['error']}")
    if result["passed"]:
        print(f"db migration journey PASSED: {result['journey']}")
        return 0
    print(f"db migration journey FAILED: {result['journey']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
