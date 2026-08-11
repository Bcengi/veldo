# Veldo DB/migration runner (reference)

A generic migration runner: it applies a set of migrations UP and DOWN against a
real database and asserts the schema and the data across the round trip. A
passing run is evidence the migrations apply, preserve their invariants, meet a
query-latency budget, and reverse cleanly, not merely that the schema loaded. It
uses the Python standard library's `sqlite3`, so there is nothing to install.

Migrations are among the highest-risk changes a product makes. An asymmetric
down (one that does not exactly reverse its up) or a lossy up is normally
discovered in production, not at review. This runner catches it at the gate.

## Use

```
veldo_db_runner.py <journey.json> [db_path]     # exit 0 = everything held
test_db_runner.sh                              # self-contained regression
```

`[db_path]` (or the `DB_PATH` environment variable) runs against a file database
instead of the default in-memory one, so the same journey can target a scratch
copy of a real database unchanged.

## Journey format

```json
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
    {"name": "one user seeded", "query": "SELECT count(*) FROM users", "expect_rows": [[1]]}
  ],
  "budgets": [
    {"name": "lookup by id", "query": "SELECT email FROM users WHERE id = 1", "max_seconds": 0.5}
  ]
}
```

Run order: snapshot the baseline schema, apply every migration's `up` in order,
apply the `seed`, assert every `invariant`, assert every latency `budget`, then
(unless `check_reversibility` is false) apply every migration's `down` in
reverse order and assert the schema returns to the baseline.

- `invariant` - the query result must equal `expect_rows` exactly (each row a
  list); a mismatch fails with the observed rows named.
- `budget` - the query must complete within `max_seconds`; overrunning fails
  with the measured time.
- reversibility - after all downs, the schema (`sqlite_master`, minus
  auto-created indexes) must match the pre-migration baseline; a residual or
  missing object fails, named. Set `check_reversibility` to `false` for a
  deliberately irreversible data migration and rely on invariants alone.

A SQL error in any statement is a named failure at that migration and statement,
never a silent pass. A failed check stops the run and exits 1 with the offending
step named; a runner that pressed on past an un-reversed migration and reported
green would be worse than none.

The `fixtures/` pair demonstrates both outcomes: `pass.journey.json` creates a
schema over two reversible migrations, seeds rows, asserts row-count and
distinctness invariants and a lookup budget, and reverses cleanly (exit 0);
`fail.journey.json` ships an asymmetric down (its up creates two tables but its
down drops only one), so a table remains after the down and the reversibility
check fails with the residual object named (exit 1).

## Why it is a reference

It ships working and self-tested, but a repository wires it to ITS database and
ITS migrations, then points the gate's `migration` (or `data`) slot at it. The
runner's control logic - applying migrations, invariant comparison, the latency
budget, and the schema-diff reversibility check - is unit-tested in
`scripts/selftest.py` against an in-memory sqlite database, so the every-commit
gate proves the logic with no external service. The veldo home repository has no
product database of its own, so it does not run the runner in its own gate; it
ships it for repos that do.
