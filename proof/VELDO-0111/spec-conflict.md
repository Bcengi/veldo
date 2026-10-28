# VELDO-0111 AC4 dependency cycle

Owner approved on 2026-10-28: Telegram 37442, "all 3", answering
Telegram 37440 item 1. The approved text is applied in the specification
under "Amendment, 2026-10-28". Round 2 below is historical.

VELDO-0111 AC4 requires driving stand-down propagation through VELDO-0113,
VELDO-0114 and VELDO-0122. Each of those specifications declares VELDO-0111
in depends_on. The implementation prerequisite points from each consumer to
0111, while the current acceptance obligation points from 0111 to each
consumer. This forms three acceptance cycles. Their implementations are absent
at the round 2 starting revision 4800972e.

## Proposed amendment

Approved replacement of only the AC4 consumer-integration sentence:

"VELDO-0111 verifies the receipt validator and exact named stand-down contract
for VELDO-0113, VELDO-0114 and VELDO-0122. End-to-end propagation through those
consumers is verified by their own acceptance suites when they land. Each
consumer must drive the VELDO-0111 fault matrix and prove that every required
row emits STANDS DOWN with census_incomplete for every incomplete receipt."

Keep the existing loss-free capture, matching failure, drain, fault generation
and complete-empty-trace falsifier requirements. The adapter checks here do not
claim that any consumer has been integrated. The approved amendment resolves the acceptance cycle. Consumer integration
remains required in each consumer ticket; it is not claimed by this fixture.

Evidence: round2/spec-red.json records the absent conflict record;
round2/spec-green.json checks the proposed amendment and records the same four
specification digests. This check establishes documentation, not owner approval.
