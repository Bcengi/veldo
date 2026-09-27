# Architecture review fix

Local main at 7df42187524b329a2241e056e125fa3043e19df5 was merged into
build-veldo-0129 before reproduction. The architecture suite reproduced two failures:
VELDO-0053 architecture/entries-blocked and
VELDO-0053 architecture/forbidden-review-launch.

Commit 4ffbfbe05762f2e6c3e0d3caa3c490fef7ff2ef6 added an empty-acceptance check in Executor.run that treated the inherited
LoopSteps.accept_proof omission as a failed implemented acceptance. Its valid build
therefore stopped at missing_authority:proof_acceptance before reaching review.
When architecture changed during that build, the same early stop concealed the
architecture refusal. The predicate itself had not been removed.

The base control-logic seam now returns NotImplemented for its absent proof service.
Executor records no accepted bundle for that seam and proceeds to the existing
review decision. An implemented acceptance returning None or an empty mapping still
refuses. LiveLoop always implements acceptance and requires its actual proof service;
the stored-proof floor and finding 129's empty-acceptance mutation remain enforced.

Runtime._run already required the provider_request decision, but its entry was absent
from EL.REGISTRATIONS. It is now registered. Suite 52 includes the module in its
existing call-site inventory. Suite 53 adds a production-copy anchor and one driver
for the registration, exercising both build and review before the Runner seam.
All existing suite 53 assertions, including both reported rows, are unchanged.
The driver requires the two callers to agree and retains their individual outcomes.

worker129-runtime-architecture-bypassed removes that runtime predicate boundary on
a temporary production copy. Its target is suite 53's architecture/entries-blocked
row. Mutation names were checked for uniqueness across every finding.

The first full selftest then exposed nine rows in older drivers that had not been
updated for VELDO-0129's required stored contextual proof:

- VELDO-0056 candidate/rejection-leaves-trunk
- VELDO-0056 candidate/named-policy-refusals
- VELDO-0056 candidate/observations
- VELDO-0056 ran/candidate/rejection-leaves-trunk
- VELDO-0135 offers/no-reclaim
- VELDO-0135 offers/floor-station
- VELDO-0135 offers/finding-path
- VELDO-0135 offers/end-to-end
- VELDO-0135 offers/observations

That run subsequently aborted in VELDO-0128's setup with missing_evidence:proof_bundle.
The offers and reports drivers now store proof through the real ProofService, with
specification revisions, evidence digests and bound gate observations. Their assertions
are unchanged. The candidate driver requires its invalid-proof build to refuse before
review, then still drives the lander's refusal and unchanged-trunk checks. Its exact
expected refusal list now also requires missing_authority:floor_record, because no
floor record is created for the refused build. No production proof check is relaxed.

The complete rerun at c82c9de86f239cba454a337f24f890b76dbc6996 finished with
6887 passed, 0 failed across all 122 suites, exit 0. Finding 129 rejected all 15
mutations and finding 53 rejected all 52, each with a green baseline, using two jobs.
The new runtime bypass specifically made VELDO-0053 architecture/entries-blocked red.
The Git subprocess boundary reported pass with no findings. Template sync compared
232 byte-identical pairs. The all validator exited 0. Selected architecture, eligibility,
candidate, offers and reports suites also completed with zero failing rows; their
partial-run exit code is 2 by design.

[Validation](architecture-validation.json) records commands, output digests and the
complete-run summary. [Mutations](architecture-mutations.json) records every rejected
case and its failing rows. [Original regression](architecture-regression.json) records
every original architecture entry outcome; [first full run](architecture-first-full-run.json)
records all nine failures and the setup abort. The new bypass's exact edit is in
[its mutation diff](worker129-runtime-architecture-bypassed.diff).

The repository gate was not run and no gate stamp, independent review, push or landing
is claimed. Gate byproducts are restored before the final evidence commit.
