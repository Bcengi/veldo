# VELDO-0111 round 2 evidence

REMAINING acceptance, with concrete local fixes and named limitations.
See ../OPEN.md and ../spec-conflict.md. Round 1 receipts remain historical.

* fault-red.json records that all three swallowed faults escaped the old AC4
  row. fault-green.json records detection of each mutant, followed by a green
  suite control. Compressed logs retain the exact receipts. FAULTS now specifies
  lifecycle state, category and capability; the row checks all three.
* extensions-red.json records the old accepted/implicit/socketcall row red.
  extensions-green.json records it green and both CLONE_UNTRACED variants
  protected. The retained escape mutant makes its own row red; invalid clone
  flags make the mutant safe to execute without leaving an untraced child.
* qualification-red.json records the blanket-failure and missing-probe failures.
  qualification-green.json and its compressed log retain the expanded generated
  operation inventory, io_uring completion, named limitations and complete suite
  control. The successful qualifier unit control uses synthetic input only.
* reason-mutations.json removes each named qualification reason in turn from
  replayed live evidence. Every removal is red and each original control green.
  This establishes preservation of the limitations, not coverage of those gaps.
* spec-red.json and spec-green.json establish the added owner-conflict record.
  They retain unchanged digests of all four affected specifications. No owner
  amendment is inferred from a green documentation check.

Each driver records source/suite digests for its own phase. Later commits can
change those digests; earlier passing controls are not presented as runs of the
later implementation. The final qualification control records the final code.

Only the single ticket suite file and its own falsifiers were invoked. Every
execution was prefixed with the owner's wait_no_load_run.sh command. No suite
set, full gate, verify.sh, push, merge or detached monitor was run. Drivers use
scratch copies and do not overwrite the worktree implementation.
