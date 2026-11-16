# VELDO-0318 proof

Implementation 1960cc219e97ca7874e3a58bdaa371cccde8b163. Builder evidence, not independent review. All four
criteria remain pending the lead gate and independent review.

## Rebase and adaptation, 2026-11-16

The three build commits were rebased onto the accepted VELDO-0327 (4a705a98) with no conflict
(a9628b86, bf487675, 6afcbc5b), then adapted to its fix round 1, F2, in e3e986ef and 1960cc21.

The terms carry the member commits: the unlanded tips rule 5 reads. The file list is the
uncommitted state Discard removes, what the snapshot saves, and no longer every tracked file. A
clean tree with only unlanded commits is asked about with an empty file list; its brief says
Discard removes no uncommitted file and the commits stay on their branch. Save and Discard run
only while the commits shown are still the tip: a commit made after the request was shown refuses
the removal, the worktree stays, and the next request names the new tip. A request that cannot be
built leaves the deferral written and is said in the result.

Rows added, each with a teeth case seen red in the final run (falsifiers.json, commit_only_worktree):
commits/request (terms without the commits), commits/discard-keeps (a clean tree treated as a
failed snapshot), commits/save (Save invents a commit), commits/late-commit (no commit comparison).

Final figures: 38 ticket rows green; 0327 27, 0312 41, 0317 23 and 0345 31 rows green. Finding 318
ran last on a clean tree at 1960cc21: 15 registered, 15 executed, 15 rejected, no reuse, no invalid
result, no surviving worker (teeth-run.json). An earlier run at e3e986ef rejected 14 and declared
the first new case invalid because the fixture stopped where no request existed; teeth-run.json
keeps that result. teeth312-summary.json and initial-teeth-summary.json are from the first build
and were not rerun.

Reported, not built or changed:
- The kept worktree's pin release after a no-space end. VELDO-0327's History (fix round 1, F4)
  names it as this ticket's, and no criterion or earlier History line of this specification
  assigns it. It waits for the lead's decision.
- VELDO-0300 ac3/commands is red since the first build of this ticket and green on the 0327 base:
  the row forbids a force option as a string in the remover source, and the settled Discard
  remover names git's force option (AC3). The suite is outside this footprint.
- VELDO-0301 ac4/no-clock is red on the 0327 base too.

The sections below are the first build's account; where they give counts, the figures above
replace them.

## First build

Signal reserves an immutable request on the deferred worktree. Repeated ending events use
that request. A refused settled removal retires its authorization and reserves a new request.
The existing service worker publishes signed terms and framing on start and journal events,
and consumes settled Save and Discard effects. A notification during an active task schedules
one followup, including after failure. No timer was added and no disk work runs on the service loop.

Keep requires an owner-signed space_disposition packet. Its command has principal, operation,
command_id, nonce and parameters containing item, version and request (the settled request id).
The ledger checks the signature, active key, active person and project_owner over space again
inside the transaction. It derives by from that principal and writes the mark and kept state
in one command. An edge-signed answer alone does not write owner_keep. The authority service
accepts this packet through its ordinary signed command entry. The console is a later ticket.

Save snapshots first, uses the installed repository identity (or a plain repository's configured
identity), creates the ticket or run kept branch, and commits only for a settled Save with changes.
Ignored work stays outside git. Discard compares the shown list before saving. Both move through
git's non-forced worktree move, probe under the marked name, compare there and move back on refusal.
The keeper retains commits and append-only snapshot attempts. Only settled Discard uses force.
Detached Discard branch creation and review grouping remain their separate tickets.

34 ticket rows passed in the targeted run and final teeth baselines. The 0312 regression suite
passed 41 rows and 0327 passed 22. Partial selftests deliberately return 2 and are not aggregate
unit or integration evidence. Finding 318 ran last: 11 registered, 11 executed, 11 rejected,
zero reuse, invalid results or surviving workers. These include all 10 specification falsifiers
and the lost-wakeup mutation. The two migrated 0312 cases also rejected their mutants.
An earlier run rejected nine cases and declared two invalid because destructive mutants made
later fixture steps abort. The fixture now preserves all row observations, and the original-path
mutant does not try to move an unmoved worktree back to itself. The full final run supersedes that
attempt; initial-teeth-summary.json retains its result. Each final mutant was executed once.

Validation, docs, template sync and lint passed with nice priority 10. The Signal diagnostic
suite passed 17 rows and failed its no-imports row. The json import exists at dependency base
f2ed9f0f, line 616; this is source-confirmed baseline behavior, not a claimed baseline rerun.
No suite numbered 151 or above, full gate, policy checker or live engine was run. No space
supervisor survived any run. No protected repository path changed.

Fixtures use temporary Git repositories, real SQLite, real generated signatures, the ordinary
inbox/presentation/settlement chain and real snapshots and removers. Telegram delivery, process
facts, pool free bytes and Docker reads are fixture inputs. The 0312 suite retains its settled
request fixture while using real signed Keep commands. No production data or other account's
process-reader configuration was touched. The host reader remains the owner's installation task.

The worktree was unchanged throughout the final teeth run. This bundle was written from its
output afterwards. Every artifact is smaller than 1 MB. The lead runs scripts/verify.sh through
the gate lock; this bundle does not claim that gate passed.
