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
