# Veldo static-invariant guardrail runner (reference)

Some rules are not about one call site; they are invariants that must hold
across the whole source. The service layer never imports the database module
directly. No file carries a forbidden token. A layer boundary is never
crossed. A single failing test cannot catch these, because the violation can
appear in any file added later. This runner turns such an invariant into a
mechanical guard: it scans the real source tree and fails the moment any file
breaks a rule.

## guardrail_runner.py

```
guardrail_runner.py <rules.json> <target_root>     # exit 1 on any violation
```

It reads a rules file, resolves each rule's glob under `target_root`, scans
every matching line against the rule's forbidden pattern, and reports each
violation as `file:line: rule-name`. Exit 0 = every rule holds, 1 = at least
one violation, 2 = the rules file is invalid (a malformed config fails loud, it
never scans nothing and passes).

### Rules file

```json
{
  "rules": [
    {
      "name": "no-db-import-outside-repository",
      "glob": "**/*.py",
      "exclude": "repository/**",
      "pattern": "^\\s*(?:import\\s+db|from\\s+db\\s+import)\\b"
    },
    {
      "name": "no-legacy-global-singleton",
      "glob": "**/*.py",
      "pattern": "\\bGLOBAL_STATE\\b"
    }
  ]
}
```

Each rule needs three things: a `name`, a `glob` of files to scan (relative to
`target_root`, standard recursive glob so `**` spans directories), and a
forbidden regex `pattern`. The optional `exclude` glob removes files the rule
does not govern: the repository layer is where the db import is allowed to
live, so "no db import outside the repository layer" is one rule over the whole
tree with `repository/**` excluded.

## Fixtures

`fixtures/rules.json` is the shared rule set. `fixtures/pass/` is a clean
sample tree (a repository, service, and api layer) that satisfies every rule,
so the runner exits 0. `fixtures/fail/` is the same tree with one deliberate
violation: `service/user_service.py` imports `db` directly, past the
repository, so the runner prints that file and line with the
`no-db-import-outside-repository` rule name and exits 1. The failing tree keeps
its own `repository/user_repo.py` importing db to prove the `exclude` glob
still allows the repository layer.

```
guardrail_runner.py fixtures/rules.json fixtures/pass     # exit 0
guardrail_runner.py fixtures/rules.json fixtures/fail     # exit 1
```

## Why this is a reference, not mechanical here

The runner is stdlib-only Python, so its control logic (rule loading, glob and
exclude resolution, the per-line scan, and the exit code) is gate-tested in
this repository's unit self-test over both fixtures, with no external
dependency. But the veldo repository has no architecture-invariant slot of its
own to run, so the runner ships `reference`: an adopting repo points a
guardrail gate slot at its own rules file and source root. It is a shipped
artifact you wire in, never a check the veldo gate runs on itself.
