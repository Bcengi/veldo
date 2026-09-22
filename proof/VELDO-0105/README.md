# VELDO-0105 proof

Implementation commit: 704d2e1. Gate GREEN there against a clean tree. Author: Ava (Claude), who also
tested it under Dmitry's Codex-out rule; Codex validates it in the batch of 2026-09-22.

## Why this item exists

VELDO-0104 shipped the fix-validation rule behind an owner flag. Turning that flag on was tried
against the whole corpus before it was committed, and thirteen proof bundles that shipped months ago
went red: VELDO-0001 through VELDO-0012 and one more. They carry a review and fix commits after it,
which is exactly what the rule refuses, and no validation record, because the runner and the assessor
that produce one did not exist when they landed. VELDO-0012 showed eight fix rounds against a cap of
two and parked retroactively.

The rule was doing what its specification says. What the specification never said is where it starts.
A gate binds the work that comes after it, not the work that shipped before it existed.

## What landed

`start_line_from_policy` reads `fix_validation.from_commit` from the parsed policy and nowhere
else, for the same reason `flag_from_policy` reads the flag from there: a check that works out
whether it applies from a field the author writes binds only the authors who volunteer it, and the
party this rule gates is the author of a fix. `.veldo/policy.yaml` is a protected path, so the owner
sets the line and the gated party cannot move it.

`start_line_scope` considers both the manifest commit and, when available, the commit that last
changed the bundle. Either position at or after the line keeps it in scope. Exclusion requires
every considered position to be conclusively before the line (outside its descendant history);
this includes a branch that forked before the line in complete history. An old manifest commit
alone cannot exempt a bundle changed after the line. Unknown ancestry, including incomplete
shallow history, stays in scope. No line recorded, an unresolvable line and a malformed line
also leave every bundle in scope.

Suite 44 already demonstrates these limits in proofcheck/start-line-excludes-history,
proofcheck/backdating-the-manifest-buys-nothing, and proofcheck/unanswerable-ancestry-fails-closed.
This describes the existing decision and rows; it adds no new executable case.

The scope test sits in `check_bundle` after the commits are known to exist and before anything is
judged, and the one call site prints the line's state on every result beside the flag's.

## What the evidence is, and what it is not

Eight rows in `scripts/suites/44_veldo_0105_startline.py`, over a REAL git repository with a trunk
carrying the line partway along it and a branch that forks before it. Each of the three declared
falsifiers is driven: the ancestry test inverted judges the history it should have left alone; a copy
treating an unresolvable line as excluding everything lets through the bundle it should refuse; a copy
preferring the manifest over a supplied policy line reads the author's start line.
The teeth-20260922 extension now also drives the exact declared fallback: with the policy
line absent, `proofcheck/start-line-not-author-writable` plants a later, resolvable manifest
line in an older bundle and requires no recorded line, continued applicability, and refusal
for the missing validation record. `python3 scripts/check_teeth_mutations.py --finding 3`
drives a top-level manifest fallback, a nested `fix_validation.from_commit` fallback, and
manifest precedence over a supplied line. Each makes that named row fail its assertion in
a completed suite run against a temporary production copy. AC3's set was expanded in the
spec's prose history; its owner-only claim, falsifier, and status are unchanged. A seventh row is the
negative control, a copy carrying only an added comment, required to agree with the original on every
case the others turn on, so the difference each mutant shows is the mutation and not the copying.

The corpus row, proofcheck/the-corpus-this-item-exists-for, reads this checkout's proof/*/manifest.json
files and any corresponding validation records. It calls check_bundle in-process with required=True
and an explicit start_line argument: first the empty string, then this checkout's dynamically
resolved HEAD. It requires more than 100 manifests, at least one refusal without a line, and no
refusals with HEAD as the line. This measures the library decision over the real corpus, not a CLI
validator run or policy-file loading, and does not pin a commit id.

Writing the real policy file and restoring it in a finally block was the historical procedure.
The current row does neither; it passes both settings directly to check_bundle.

**What this does not show.** Every row here is a check somebody wrote, so it can only find what a
check was written for. It shows the scope decision is made where it should be and cannot be moved by
the party it gates. It does not show that the line is set to the right commit, which is an owner act
on a protected path and deliberately not part of this build.

## Rollback

Remove the recorded start line. The rule returns to judging every bundle, which is the behaviour
VELDO-0104 shipped, and no evidence is invalidated.
