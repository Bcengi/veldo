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
collector archives the complete clone, scratch and TMPDIR trees and engine output outside
the deleted roots, and returns a file reference with a SHA-256 digest. An explicitly
empty collector retains the directories. A failed cleanup retains the hold until
signed cleanup or operator release arrives.

The client stores the signed result request on the Mac before transmission, retries
transport failures with exponential backoff and jitter for up to eight attempts,
and retains the acknowledgement. Exhaustion leaves the request for the next
receiver invocation; it never repeats execution. Replay
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

## Follow-up review corrections

Local Mac capacity now retires from the authority's committed release outcome,
separately from collection and OS cleanup. Empty collection, failed cleanup and
incomplete retirement keep their files and hold until an authorized release.
An operator release then retires even a local unknown slot. Slot replacement
fsyncs the contents and directory. A saved result acknowledgement can finish
local retirement after a receiver crash without contacting the authority.

The authority uses the existing configured receiver argv under
`receiver.configs[repository]` -> `remote_receivers[host].argv` (or directly under
`receiver.remote_receivers`) to send a release-only wake after commit. The Mac
queries `worker_status` over its signed relay and checks dispatch, contract and
host before writing the local slot. Untrusted wake input cannot authorize a
release. A bounded background delivery lets the authority continue serving that
status request. Committed retired reservations form the durable release outbox;
authority startup and command replay redeliver, and receiver restart can consume
the stored outcome. No recurring factory timer is added. An unavailable Mac
remains queued in that durable state for replay or restart; no transport can
synchronously change a disconnected host.

Replaying a committed release also reissues the capacity wake, covering a crash
between transaction commit and scheduling. A late measured result after operator
release or unknown cleanup advances the report sequence on the original
reservation invocation. These are cumulative corrections, not additional
invocation charges. Duplicate delivery leaves the measured charge unchanged;
an unexpected preexisting first report still refuses atomically.
If the exit was already recorded without usage, its first measured usage can
fill that gap while preserving the signed exit and references. Previously
measured usage remains immutable. Delayed local observations also cannot
overwrite a retired Mac slot, and a release arriving before bootstrap retains
a tombstone that prevents a late launch of that dispatch.

The default archive includes TMPDIR contents before deletion, preserving output
linked from the clone into temporary storage. Archives remain file URIs on the
Mac; this change does not transfer or expire them.

The [follow-up verification record](b2-release-falsifiers/verification.txt) binds
the tested source digests and records 17 relay rows and 36 routing rows passing,
with no failures. Both commands exit 2 because selected suites are PARTIAL.
The ten adjacent falsifier diffs and failure excerpts demonstrate the named
regressions on the implementation commits recorded there. These are Linux
fixtures with signed requests, real SQLite transactions, a child receiver over
file-backed test transport, and simulated Mac OS observations; no live SSH or
macOS qualification is claimed. The full gate remains the reviewer's work.
