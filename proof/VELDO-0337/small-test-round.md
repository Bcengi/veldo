# VELDO-0337 accepted re-review: two missing guard rows

Base: cb6c48fe, branch veldo-space-0337. Test-only follow-up to the accepted
re-review dated 2026-11-15. Product code is unchanged; dispatch.py and
control_space.py still equal their engine/.veldo copies.

- ac1/reconcile-domain-and-repository: for each foreign coordinate separately,
  a durable passing verdict names a dispatch whose items are still held. The
  fixture changes the stored record's domain or repository after the interrupted
  verdict send. Reconcile sends nothing, writes nothing, and preserves item
  versions, states and planted files. Removing the domain/repository filter is
  registered as space337-reconcile-foreign-scope.
- ac1/adopt-refuses-ends: an adoption command carrying the valid subset
  [verdict_recorded] is refused with invalid_input:ends, without item or journal
  changes. The same adoption without ends succeeds and retains all kind events.
  The shared command builder supplies ends because the public adopt helper has
  no such argument; the real adoption transaction enforces the refusal. Removing
  the adopted condition is registered as space337-adopt-accepts-ends.

Both mutations are registered under finding 337. The mutation driver uses
temporary production copies; the existing canon row checks the synced files.

Requested diagnostic run:

    python3 scripts/selftest.py --suite 153_veldo_0337_verdict_recorded

45 passed, 0 failed: 19 ticket rows and 26 shared checks. Exit 2 is the required
partial-run convention. Raw output: small-test-suite.txt. This is a diagnostic
record only, not aggregate verification, a passed unit-evidence claim or a
landing decision. The earlier manifest and its historical runs are unchanged.

The first mutation run executed all 18 cases and rejected 17, including both
new mutations. The existing space337-before-commit mutation interrupted the new
fixture before its verdict existed; indexing that missing review omitted the
last suite row, so the runner correctly rejected the result as missing_target.
The fixture now checks for a review before reading it, reports a false assertion
and continues through every row. No mutation definition or runner check was
weakened. The subsequent suite run again reported 45 passed, 0 failed.
