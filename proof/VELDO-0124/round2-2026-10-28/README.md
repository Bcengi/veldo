# VELDO-0124 round 2, 2026-10-28

Status: REMAINING for real Claude login, complete qualification and independent
review. Read `../OPEN.md` for the concrete owner action. Review input was
`../review-2026-10-28.md` at baseline `e20b4c15`. Runtime fix: `96901dbf`.

## Evidence verification

Both canonical and installed profiles resolve every required evidence reference,
require a file in protected storage, hash the exact bytes that are parsed, and
match native kind, profile digest, host, OS version and the passing row. Row
references are objects containing `path` and `digest`; observation documents use
`veldo.macos_worker_evidence/v1`, `kind: native`, `profile_digest`, `host`,
`os_version` and a `rows` object mapping engine/row names to `passed`.

`qualification_falsifier.py` loads an isolated copy of the reviewed profile for
RED, then the fixed profile for GREEN. The handwritten record must refuse before
bootstrap. The same check covers missing files, wrong digests, malformed rows,
edited evidence bytes, substituted host/profile bindings and blocked results.
Intact evidence still admits. The synthetic fixture files explicitly identify
themselves as logic fixtures and confer no native qualification.

All local runs use the blocking shared gate lock. Only owning suites 103 and 104
and ticket falsifiers are run. Their partial exit code 2 is expected and is not a
full gate or a landing decision. `qualification-red-green.json`, the two suite
logs and `falsifiers/negative-controls.json` hold the exact results. The new
single change mutant removes the evidence verifier call and must fail the
`AC1/forged-qualification` row.

The reviewed profile falsifier exits 1 with the expected missing refusal; the
fixed profile exits 0. Suite 103 has 29 owning rows and 55 total checks passed,
zero failed, partial exit 2. Suite 104 has 7 owning rows and 33 total checks
passed, zero failed, partial exit 2. All ten single change mutants are rejected on their
named rows, including removal of `verify_evidence`. The unchanged runtime files
are restored after every mutant because mutation runs use isolated copies.

## Real engine child

`drive_real_qualification.py` creates signed, accepted dispatches and pre-call
reservations in an ephemeral local authority store. It sends only non-secret
candidate data and code to the Veldo directory on the Mac. Both engines have a
prepared descendant request. Claude's offline status check blocks its row; one
real Codex 0.154.0 call executes the foreground child script. No credential is
copied and no detached command is used.

`native-engines-qualified.json` records child PID 90732 in coalition 20494,
with real engine PID 90692. The child installs signal handlers before its ready
marker, records SIGTERM and continues. The supervisor progresses through
cooperative, terminate and kill. Stop takes 3.137 seconds. Before cleanup or
slot release, the runner asserts OS exit, the child's disappearance, an empty
coalition and a known lifecycle outcome. The released pool has zero pending
slots. There are no stray launchd jobs after cleanup. Raw engine output is
parsed for accounting and deleted on the Mac.

The real call is bounded by a 115 second contract and 120 second profile cap.
The profile permits at most two workers; this harness runs sequentially and
made one model call. `authority-ledger.json` records configuration and binary
digests, accepted dispatch identities, observed usage and retained unknown
provider accounting. The CLI observation file exits 2 because Claude is blocked;
the coordinator exits 0 after recording both results. No qualification is minted.

The prior three Codex rows and three blocked Claude rows remain in
`../native-2026-10-28/native-engines-qualified.json`. The new prepared Claude
child row is an additional blocker under the same login issue. The current
Mac observation agrees with that earlier login diagnosis.

The prepared Claude child runner selects Claude's own stream meter when login is
unblocked. That branch remains unexecuted on the real CLI until the owner action;
the recorded Codex branch uses the same meter as the observed run.
