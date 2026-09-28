# VELDO-0148 proof

A land refused because another factory moved main ends its original dispatch. The installed
factory service offers a new land dispatch, with a new watermark, merge, candidate gate and
compare-and-swap. A conflict returns to the builder and then review. A lost lease is refused
only when the fetched destination tip does not contain the candidate; containment stays unknown.
A prior grant is bound to the candidate tree. Replacement requests are allowed only when every approval problem is a tree-only binding
mismatch for a prior grant at this revision. A mixed refusal keeps no subject and asks no question.
A grant is applied at most once per dispatch, failed dispatches never receive a grant, and the
station rechecks every prior grant before writing any replacement.

Suite: `scripts/suites/86_veldo_0148_re_land.py`, registered with its own prerequisite closure.
It drives real Git repositories and a disposable bare remote, the SQLite store and signed
production writers, build and review child processes, the floor and proof services, the lander,
installed candidate gate, effect executor and publication receipts. The authority service runs
from its installed executable. Another local clone moves the remote before listing or in the
publication clone's pre-push hook. Engine output comes from a generated fake; no real model,
login, external service or real credential is used. Each row reports once.

## Criterion rows

| Criterion | Row | What it proves |
|---|---|---|
| AC1 | `install/land-station` | The installation and scaffold include the land station and its production dependencies; malformed station configuration is refused by name; engine copies match and service passes have wake sources. |
| AC1 | `reland/stale-subject` | A stale-subject refusal ends the original dispatch without another attempt under it. Exactly one new dispatch follows, takes the new watermark, re-merges unchanged build evidence, re-gates and lands with its own receipt. Status counts dispatches and refusals. |
| AC1 | `reland/review-kept` | A clean re-merge retains the review of the unchanged evidence commit and the existing floor record, without another build or review. |
| AC1 | `reland/conflict-rebuild` | A real merge conflict publishes nothing, names the conflicting path and offers one new build instructed to merge the new main, followed by that build's review. |
| AC1 | `reland/never-forced` | Every recorded remote update is a fast-forward and every publication uses the exact watermark of its own land as its lease. |
| AC2 | `lease/trunk-moved` | A push between listing and publication loses the lease; the executor fetches the moved tip, refuses as trunk-moved and the service re-lands under a new dispatch. |
| AC2 | `lease/contains-unknown` | A moved tip containing the candidate remains unknown, judged at the push URL; its named stop leaves no receipt, retry or re-land. |
| AC3 | `grant/never-granted` | A never-granted security approval is refused by name, sends no owner question and writes no approval or publication. |
| AC3 | `grant/mixed-approvals` | A mismatched owner grant and missing security approval stay failed with both named reasons, no subject, question, approval write or loop action. |
| AC3 | `grant/mixed-proof` | An owner tree mismatch together with a security proof-only mismatch stays failed with both reasons and no subject, question or grant. |
| AC3 | `grant/once-per-dispatch` | Replaying an applied grant emits no accepted event and writes nothing. Three extra loop passes grow neither accepted events, refused entries nor approvals. A direct grant on a failed dispatch is refused. |
| AC3 | `grant/revoked-before-answer` | The owner answers a real question after security is revoked. The station refuses security by name before writing any replacement, including the still-valid owner grant. |
| AC3 | `grant/fresh-request` | The old tree's grant is refused by name for the re-merged tree without publishing. One owner request survives repeated passes; answering creates an exact-tree grant and the next dispatch lands that tree. |

The control row `format/fake-lines` checks each scripted engine event against the captured binary
format. The separate VELDO-0172 row `fake/capture:0148_re_land` drives the installed fake through
the shared conformance checker.

The new approval rows drive the final authorization with an owner policy update after the real
CandidatePolicy accepts and before Landing publishes. This reaches the final approval check even
though a missing approval already present at the earlier policy check stops there. Both rows use
the signed store writer, real land station, installed service inbox and signed owner answers.

## Red record

[red-at-ad916989.json](red-at-ad916989.json) replays the current suite against an unchanged archive
of the original pre-concern commit: all ten behavior rows fail by assertion and the format control
stays green. [red-at-b33e82f8.json](red-at-b33e82f8.json) replays the current suite against the commit
before this review repair: both new approval rows fail by assertion; the existing rows stay green.
[red-at-f59b3136.json](red-at-f59b3136.json) records this re-check: all four changed or new
behavior rows fail by assertion, with the existing behavior and format rows green.
No exception counts as evidence. [drive.py](drive.py) records module digests and assertion details.

## Mutations

[mutations.json](mutations.json) records the lead's reported run at f59b3136: 14 of 14
mutations rejected. This is attributed evidence supplied in the owner's brief, not a builder run.
It separately records all 18 current finding-148 registrations, source and mutant digests, exact
applied diffs and named rows. Their anchors and syntax are statically checked; execution on this
repair is pending for all 18, including the four added here. No current rejection is claimed.
[mutations-before-review.json](mutations-before-review.json) preserves the earlier builder's
12 rejections as historical evidence.

The repeated-question mutation varies both alias and command identity. The updated missing-grant
mutations restore an invalid replacement subject. The four added mutations restore the mixed-case
question, allow a proof mismatch, reapply a grant and overwrite a revoked approval.

| Mutation | Named row |
|---|---|
| `reland148-stale-left-failed` (AC1 falsifier) | `reland/stale-subject` |
| `lease148-loss-unknown` (AC2 falsifier) | `lease/trunk-moved` |
| `grant148-old-tree-accepted` (AC3 falsifier) | `grant/fresh-request` |
| `reland148-loop-offers-nothing` | `reland/stale-subject` |
| `reland148-conflict-relanded` | `reland/conflict-rebuild` |
| `reland148-rebuild-not-reviewed` | `reland/conflict-rebuild` |
| `reland148-landed-rebuilt` | `reland/review-kept` |
| `reland148-end-wakes-nothing` | `reland/conflict-rebuild` |
| `lease148-contained-refused` | `lease/contains-unknown` |
| `lease148-tip-not-fetched` | `lease/trunk-moved` |
| `never148-forced-push` | `reland/never-forced` |
| `grant148-asked-every-pass` | `grant/fresh-request` |
| `grant148-missing-treated-as-replacement` | `grant/never-granted` |
| `grant148-replacement-includes-missing` | `grant/mixed-approvals` |
| `grant148-mixed-question-restored` | `grant/mixed-approvals` |
| `grant148-proof-mismatch-replaceable` | `grant/mixed-proof` |
| `grant148-applied-again` | `grant/once-per-dispatch` |
| `grant148-revoked-overwritten` | `grant/revoked-before-answer` |

## Replay

Run the suite with `python3 scripts/selftest.py --suite 86_veldo_0148_re_land`.
Replay the original red record with `python3 -B proof/VELDO-0148/drive.py --red ad916989`, or the
earlier review regression with `python3 -B proof/VELDO-0148/drive.py --red b33e82f8`, or this
re-check with `python3 -B proof/VELDO-0148/drive.py --red f59b3136`.
For reviewer use, `python3 -B proof/VELDO-0148/drive.py` regenerates mutation evidence with at most
two workers. The builder did not run that mutation mode or the mutation checker.

## Completion checks

This re-check runs only suite `86_veldo_0148_re_land`, serially, in the ordinary environment
and the requested empty gate environment. These are partial checks, not a full gate verdict;
subset mode intentionally exits 2. Final counts and the footprint, anchor and validation results
are recorded in the specification History. Engine copies match their repository counterparts.
The suite remains registered once and requires.json was regenerated. No other suites, full gate
or mutation execution run in this repair.
