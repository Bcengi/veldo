# VELDO-0327 proof

Implementation: b1f15b3b499bac2ad244122b02e9416336c24a79. Builder evidence, not independent review.
All four criteria remain pending the lead's canonical gate and review.

The journey adds space_disposition, a decision for the project owner with one approve effect,
space_disposition_decided. The signed terms and displayed brief bind the three picks, file list,
save-before-remove explanation, restore command, and detached commits' kept branch. Terms with
an empty or missing list are refused before any request opens. The inbox transaction also checks
opens and revisions against those terms, so a signed request cannot hide the list or add a choice.
The existing settlement commits the choice, effect obligation, receipt and terminal request once.
It retains its existing owner, current presentation, unoffered-choice and rollback checks.
No tier field, ruling or channel choice mapping was added.

The five original touchpoints and their fifteen Telegram answer/effect cases remain. Their legacy
suite now names the new journey entry in its cardinality check and leaves its original matrix
intact. The spec footprint records that compatibility adjustment.

## Interface for the next ticket

The terms touchpoint is space_disposition and the target kind is space_item; target.ref is the
listed item's id. The proposal has exactly discard (SPACE_DISCARD) and worktrees (one member).
Each member carries item, path, branch (null if detached), unheld_commits (a boolean), kept_branch
(null unless needed), files (a nonempty list of paths), and restore (the shell-quoted command
veldo space restore followed by the item's id). An unknown or empty list raises no request.
space_presentation(proposal) returns the kind, brief and choices for the ordinary signed inbox
open. The producer adds its owner, scope, deadline, budget and the recorded terms subject.
A change to the list needs new immutable terms and a revised request/presentation.

The effect is the existing obligated settlement record with the exact choice and proposal. This
ticket introduces no removal, snapshot, git operation, polling or service-loop worker. VELDO-0318
owns request triggering and filesystem application through the keep step and removers. Review
groups and member picks stay with their later tickets. This proof does not claim those actions ran.

## Rows and checks

22 ticket rows and 26 shared checks passed in the targeted diagnostic run. The existing settlement
suite passed 8 rows, and the inbox suite passed 18, each with the same 26 shared checks. All three
partial runs returned their required exit 2. checks.json records them as diagnostics, never as
aggregate verification. The final teeth baseline independently recorded all 22 ticket rows green;
rows.json maps every AC to those observations.

The new suite uses temporary SQLite, real generated signing keys, signed membership and API edge
answers, the real inbox, presenter and settlement, and a fixture Telegram send transport. It reads
both the rendered single/multipart presentations and committed journal transitions. It checks all
three choices, refusal without a file list, missing branch and recovery text, hidden/revised lists,
a person without the project-owner role, stale bindings, unoffered choices, repeat settlement,
transaction failure and recovery, and the original five touchpoints. It uses no real engine,
remover, host worktree or other account's process reader. Production data and protected objects
are untouched. No protected repository path changed.

Validation, docs hygiene, template sync and lint passed with nice -n 10. Each run left no space
supervisor. Suite 86_veldo_0127 was left alone. No suite numbered 151 or above ran. The full gate
and policy checking remain with the lead. The fast checks preceded the final proof write.

## Falsifiers

Finding 327 ran last on the committed implementation, with two workers and nice -n 10.
Eight registered, eight executed, eight rejected, zero reused, zero invalid results and zero
surviving workers. Each mutation was applied once; every baseline and no-change control was green.
The four specification falsifiers are bare choices, an empty file list, the ruling written in
place of the chosen pick, and six rulings. The empty-list mutant publishes the incomplete request;
the presentation row observes it and fails. Four additional mutants remove the request/terms
binding, detached-branch requirement, save explanation and restore-command check.

teeth-receipt.json holds the full runner receipt; falsifiers.json is the compact red-row summary.
The tracked-file digest before and after was 7a2a966c902a632488d1b6e01be0b63d1c75f337ae0d6c9ff821019b6f910084.
Both worktree status reads were empty. No worktree write occurred during teeth, and no test or
check ran after it. Only this proof bundle was written afterward. No space supervisor survived.
Every artifact is below 1 MB; transient logs remain in /tmp/veldo0327-build.

The verify command is ./scripts/verify.sh, for the lead to run through the gate lock.
Rollback: revert the implementation. No work, snapshots or kept refs are removed by this ticket.

## Fix round 1 (review of f2ed9f0f, verdict FIX)

Rebased onto the accepted VELDO-0317 (39a6387b) with no conflict; the 0317 suite passed 23 rows after
it. Implementation after the round: d762312c5d6fd4711f347839cb07f2e56b7ccf5a. Builder evidence of the fix round, not independent review.

F1 (high). The check that a space request shows what its terms require was a command override on the
Settlement's own connection, so whichever Inbox was built last decided whether it ran. It is now
request_problem in the settlement module, registered at module level in control_assignment.py as the
subject validator for settlement terms (the module loads its sibling by its own path on first use).
Every Inbox consults it inside its own open and revise transaction, and the Presenter consults it
before it frames and before it presents (refusal presentation_mismatch). The Settlement's override is
removed. Rows fix1/late-inbox (an Inbox built after the Settlement), fix1/no-settlement (a second
connection that has no settlement command) and fix1/presenter (an unmatched stored request is neither
framed nor presented). The footprint widening is recorded in the spec History as the lead's.

F2 (medium, lead decision). Each worktree's terms gain the member commits, the tips of the unlanded
commits. One of files and commits is non-empty; both empty is still refused. With no file the brief
says "Discard removes no uncommitted file; the commits stay on" and the branch (the kept branch when
detached), and the tips are listed. AC2 and its falsifier are amended in the spec. Row
fix2/commits-only: a clean tree with one unlanded commit is presented with the three picks, accept
discard settles, and the effect's proposal still names the commit and its branch. This ticket records
the obligation; that the commits survive on disk is VELDO-0318's to show.

F3 (low). Row fix3/target-item: terms whose target names another item, or another kind, are refused.
F4 (process) is recorded in this spec's History; the VELDO-0317 spec is outside this footprint.

Interface change for VELDO-0318: the worktree member now has eight fields, with commits (a list of
commit ids, possibly empty) beside files (possibly empty when commits is not). Terms without the
commits member are refused.

Rows: 27 ticket rows passed (22 earlier, 5 new), zero failures, partial exit 2. Settlement 8, inbox 18
and full pool 23 passed; validation, docs, template sync, space boundary and lint passed; all with
nice -n 10 at the final implementation commit. The reviewer's probe file was not run; the fix1 rows
are its P1 and the fix2 row its P2. No own supervisor survived any run.

Teeth: finding 327 ran last on the committed tree, two workers, nice -n 10: 16 registered, 16
executed, 16 rejected, 0 reused, 0 invalid, 0 surviving workers. Eight are new: the write skips the
validator, the Presenter frames an unmatched request, the Presenter presents one (F1); files only,
the commits not said to stay, the tips unlisted, detached commits with no kept branch (F2); terms
that target another item (F3, the reviewer's M4). The anchors of three earlier cases moved with the
code. The digest of git ls-files -s before and after was
c056d23625461af2376a1dc87cd6fd1c7bfdc58a7a2053f5a7d1145dbea78504; the worktree was clean both times.
After teeth only this proof bundle was written, and validate.py was run once on it (pass). No suite
ran after teeth. Logs are in /tmp/v327-fix1.
