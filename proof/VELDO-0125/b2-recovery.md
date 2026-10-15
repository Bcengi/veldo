# B2 release and result delivery corrections

This round answers the independent review of 10644dd1. It is implementation and
targeted regression evidence, not a gate stamp or independent approval.

Signed host cleanup now releases an unknown outcome without requiring a recovered
termination record. The cleanup and final unknown accounting are journaled with
the release; the dispatch outcome and missing usage remain unknown.
The remote cleanup caller explicitly permits Mac supervisor retirement after
observed termination and an empty group without requiring an exit code; the local
caller's default contract is unchanged. A lost running notification stops the
run and still collects and durably delivers its terminal observation.

The trusted receiver retains result evidence before deleting inputs. Its default
collector archives the complete clone and scratch trees and engine output outside
the deleted roots, and returns a file reference with a SHA-256 digest. An explicitly
empty collector retains the directories. A failed cleanup retains the hold until
signed cleanup or operator release arrives.

The client stores the signed result request on the Mac before transmission, retries
transport failures until acknowledged, and retains the acknowledgement. Replay
uses the same command identity; the authority verifies it and returns the committed
record without duplicating spend or release. Reinvoking the receiver for that
dispatch replays its retained request without claiming or executing work again.

An active, repository-scoped person with `operations_authority` can use
`control_worker_client.Client.release(binding, reason=..., cleanup=...)`. The
binding names dispatch, unit, host and contract digest. Cleanup must attest
`terminated`, `cleaned` and `clone_removed` as true, after collecting generated
files. This command uses the same signed relay as worker commands. It records the
operator, reason, signature-bound command digest and cleanup durably; no exit code
or successful outcome is inferred. Worker service principals cannot authorize it.

A deadline-only pass still settles just its named launches. When that frees a
reservation it queues one `remote_capacity_released` wake, so the next pass offers
waiting work even when the account had no reset time. Signed releases also wake
the factory when they free capacity after the original launch has been removed.

Initial verification: `python3 scripts/selftest.py --suite 106_veldo_0125_routing`
reported 29 suite rows passed, 55 overall passed, zero failed, exit 2 (PARTIAL).
Further verification and falsifier results are recorded alongside this document.
Final [selected-suite verification](b2-recovery-falsifiers/verification.txt): relay
has 17 suite rows passed (43 overall), routing has 32 (58 overall), both zero failed
and exit 2. All seven targeted falsifiers exited 1 with named regression failures.
The verification record includes source and regression digests and mirror checks.
The current [falsifier records](b2-recovery-falsifiers/) retain exact diffs applied
to both mirrored copies and the real selected output, including exit codes. The
old recurring-tick failure claims in both earlier bundles were withdrawn because
their mutations were unreachable. Their replacement is a recurring timer installed
before `next_timer` returns; the zero-pass row drives that timer through `expire`.
Only the reviewer runs the canonical gate. No real Mac, SSH relay, provider engine,
deployment or activation is certified by these Linux fixture rows.
