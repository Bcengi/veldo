# Architecture review fix

Local main at 7df42187524b329a2241e056e125fa3043e19df5 was merged into
build-veldo-0129 before reproduction. The architecture suite reproduced two failures:
VELDO-0053 architecture/entries-blocked and
VELDO-0053 architecture/forbidden-review-launch.

The branch's new empty-acceptance check in Executor.run treated the inherited
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

Validation results are recorded after the final checks. The repository gate is not
run and no gate stamp, independent review, push or landing is claimed.
