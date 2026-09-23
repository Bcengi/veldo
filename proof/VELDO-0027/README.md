# VELDO-0027 protected signing

Status remains **ready**. This implements the signer core; it neither activates a
channel nor installs an operating-system custody boundary. Owner landing approval,
including protection of `.veldo/keys/allowed_signers`, remains separate. Policy is
unchanged. No production credential or private key is committed.

The canonical gate passed from a clean tree at `838cfebdc0084294b63850e18d68e9e1c7afec0c`:

```text
selftest: 5651 passed, 0 failed
mutations: passed registered=66 executed=66 rejected=66 workers=88 elapsed=32.968s
catalog: 8 run, 15 not-applicable (reasons on record), 0 waived, 0 undeclared
GATE: GREEN (838cfebdc0084294b63850e18d68e9e1c7afec0c)
```

Baseline gate: 620.031 seconds. Implementation gate: 638.375 seconds. Measured increase:
**18.344 seconds**, within the 60-second limit. The mutation stage changed from
23.779 to 32.968 seconds. See `timing.json` and `gate-summary.json`. Raw logs remain
outside git; `gate.log` contains only safe result lines. The two gate byproducts
are restored before the evidence commit and are never included in these commits.

## Implementation and authority boundary

`control_keys.attach/admit` registers and authenticates durable key transitions in
the existing control store. Accepted membership, current versions, steward authority,
nonces and snapshot versions govern admission. `publish` atomically derives the
public OpenSSH projection, including verification-only historical keys. A stale or
branch-substituted projection refuses until it agrees with accepted state.

`control_signer.call` starts and joins one child over anonymous pipes. The installed
caller supplies its fixed config (store, repository, public projection, external
private-key directory); a request cannot choose those locations. The child issues a
fresh challenge. A registered connection key signs that challenge and the request
digest, and verified registration determines the channel. Request channel/key fields
are cross-checks. Signing and transitions serialize through the real SQLite store.
Inherited SSH-agent discovery is disabled; the selected external key file is used.

`record` and `capture` are authority-side acquisition APIs, never sign-request
operations. Captured tool invocation, executable digest, PID, exit code, output
lengths and digests are bound to contract and actor provenance. Accepted source
records anchor edge attribution and presentation, and the signer rechecks delegation
and source fields. Signed CLI records retain and verify the personal signature.
An agent statement stays an assertion even with complete observation-like provenance.
Live platform acquisition/activation remains Package E; installation remains W32.

The existing repository architecture already includes both signing module globs.
The engine architecture receives those globs while retaining its existing adopter
settings. New runtime modules and public projection are byte-identical in both
locations. Neither new module is loaded by the validator, so no scaffold list change
is needed or made.

## Reproduce and read the evidence

- `bash scripts/verify.sh`: the only complete acceptance run. Keep raw output outside
  git, for example `/tmp/veldo-0027-gate.log`; existing negative fixtures in the gate
  can look like credentials.
- `python3 proof/VELDO-0027/drive.py --mutations`: regenerate compact observations,
  public-key digests and readable applied mutation diffs. Keys are freshly generated
  outside the disposable Git repository and destroyed on exit. It is a targeted
  development driver; only the full gate establishes acceptance.
- `python3 proof/VELDO-0027/drive.py --gate-log /tmp/veldo-0027-gate.log --gate-seconds SECONDS`:
  retain safe summary lines, the raw-log digest and compact mutation-stage results.

`universe.json` independently enumerates required rows. The suite compares that
inventory with executed row identities, and separately checks the four contract
assertion kinds across Telegram, Jira and signed CLI. No model response is required.
Stores, Git operations, Ed25519 signatures and child processes are real. Mutation
copies contain production modules only; the observation apparatus remains outside
what is mutated. Each named red result is an assertion failure, not an exception or
timeout. The required mutation stage additionally drives unmutated and no-op controls.
Applied diffs are retained as readable `.diff` files; no large encoded fixture is kept.

Process evidence samples the actual signer and its child descriptors, checks for
named UNIX/network endpoints and listeners, checks the run directory for socket and
PID files, compares signer counts, and verifies every returned signer PID has exited.
Transient unbound libc name-service probes are not signer endpoints. Process sampling
is not a claim of syscall-complete operating-system custody enforcement.

## Criteria and executable rows

### AC1

- `signing/kind/telegram_chat/decision_answer`
- `signing/kind/telegram_chat/assignment_acceptance`
- `signing/kind/telegram_chat/review_disposition`
- `signing/kind/telegram_chat/acknowledgement`
- `signing/kind/jira/decision_answer`
- `signing/kind/jira/assignment_acceptance`
- `signing/kind/jira/review_disposition`
- `signing/kind/jira/acknowledgement`
- `signing/kind/signed_cli/decision_answer`
- `signing/kind/signed_cli/assignment_acceptance`
- `signing/kind/signed_cli/review_disposition`
- `signing/kind/signed_cli/acknowledgement`
- `signing/cross-channel`
- `signing/arbitrary`
- `signing/membership`
- `signing/unknown-kind`
- `signing/delegation/absent`
- `signing/delegation/stale`
- `signing/delegation/wrong-principal`
- `signing/delegation/revoked`
- `signing/delegation/valid-control`
- `signing/process-count-and-listeners`
- `signing/children-exit`
- `signing/no-key-leaks`
- `signing/no-socket-or-pidfile`

### AC2

- `signing/branch-key`
- `signing/rotation`
- `signing/retirement`
- `signing/revocation`
- `signing/rotation-race`
- `signing/race-new-key`
- `signing/kill-after-rotation`
- `signing/kill-after-retire_signing_key`
- `signing/kill-after-revoke_signing_key`
- `signing/transition-clock`

### AC3

- `signing/attribution/platform_message_id`
- `signing/attribution/sender_id`
- `signing/attribution/platform_timestamp`
- `signing/attribution/personal-signature`
- `signing/text-only`
- `signing/captured-observation`
- `signing/assertion-control`
- `signing/assertion-relabel`
- `signing/bound/contract_digest`
- `signing/bound/source_digest`
- `signing/bound/presentation_digest`
- `signing/bound/actor`
- `signing/bound/actor_kind`
- `signing/bound/principal`
- `signing/observation-bound/stdout_digest`
- `signing/observation-bound/stderr_digest`
- `signing/observation-bound/executable_digest`
- `signing/observation-bound/invocation`
- `signing/observation-bound/exit_code`
- `signing/observation-bound/pid`
- `signing/receipt-bound/schema`
- `signing/receipt-bound/channel`
- `signing/receipt-bound/key_id`
- `signing/receipt-bound/key_effective_at`
- `signing/receipt-bound/key_revision`
- `signing/receipt-bound/signed_at`
- `signing/receipt-bound/source_id`
- `signing/receipt-bound/source_digest`
- `signing/receipt-bound/payload`
- `signing/receipt-bound/delegation_id`
- `signing/receipt-bound/delegation_version`

### AC4

- `signing/channel-comes-from-the-connection`
- `signing/key-comes-from-the-channel`
- `signing/unauthenticated`
- `signing/key-path`

Completeness assertion: `signing/universe`.

## Driven falsifiers

| Applied mutation | Named assertion turned red |
| --- | --- |
| [signing-remove-channel-restriction](signing-remove-channel-restriction.diff) | `signing/cross-channel` |
| [signing-permit-foreign-channel](signing-permit-foreign-channel.diff) | `signing/cross-channel` |
| [signing-request-channel](signing-request-channel.diff) | `signing/channel-comes-from-the-connection` |
| [signing-request-key-channel](signing-request-key-channel.diff) | `signing/channel-comes-from-the-connection` |
| [signing-request-key](signing-request-key.diff) | `signing/key-comes-from-the-channel` |
| [signing-ignore-key-crosscheck](signing-ignore-key-crosscheck.diff) | `signing/key-comes-from-the-channel` |
| [signing-text-without-identity](signing-text-without-identity.diff) | `signing/text-only` |
| [signing-text-substitutes-identity](signing-text-substitutes-identity.diff) | `signing/text-only` |
| [signing-branch-projection-authority](signing-branch-projection-authority.diff) | `signing/branch-key` |
| [signing-branch-preflight-bypass](signing-branch-preflight-bypass.diff) | `signing/branch-key` |
| [signing-prelock-clock](signing-prelock-clock.diff) | `signing/transition-clock` |
| [signing-truncated-clock](signing-truncated-clock.diff) | `signing/transition-clock` |

All twelve unmutated controls passed. Each row has two distinct defects: removal
versus conditional bypass, request channel versus request-key channel, request key
selection versus omitted key cross-check, missing attribution versus text substitution,
and worker-file authority versus false preflight success. `mutations.json` also records
any additional assertions each defect turned red. The gate result records its no-op controls.

The two additional lifecycle mutants exercise a serialization defect found during
implementation review: an effective time taken before the transaction lock can
invalidate a receipt legitimately signed before that transition. Effective time is
now sampled inside the transition; a real contending writer and a lock-release
timestamp test its ordering. The second mutant truncates that timestamp.

## Review fixes for 68ea1f3 (F-01 through F-04)

Each finding has its own implementation commit and suite 56 regression. Before each
fix, its new assertion failed against the original signer from `68ea1f3`; after
its fix, the suite passed. [review-fixes.json](review-fixes.json) records the named
RED assertions, commands, original module digest, and per-finding green counts.
These targeted runs are development evidence; full acceptance requires the gate.

| Finding | Required refusal row | Two registered mutations |
| --- | --- | --- |
| F-01 | `signing/personal-content-binding` | `signing-ignore-personal-content`, `signing-ignore-personal-ruling` |
| F-02 | `signing/rotation-requires-rebound-delegation` | `signing-ignore-selected-key-binding`, `signing-retired-key-inherits-grant` |
| F-03 | `signing/unauthenticated-diagnostic-is-empty` | `signing-leak-source-before-auth`, `signing-leak-revision-before-auth` |
| F-04 | `signing/personal-envelope-expiry` | `signing-ignore-envelope-problems`, `signing-ignore-envelope-expiry` |

F-01 compares the source's ruling and presentation id to the personally signed
command parameters. Its row preserves a valid reject/p1 signature while changing
both claims, then each claim separately; matching reject/p1 remains accepted.
F-02 requires the payload key to match the selected signing key, then uses the
existing membership contract to require the delegation's key to match the payload.
The suite rotates both signing and connection keys, refuses the old source/grant,
refuses a source-only update, and accepts an explicitly superseded, rebound grant.
F-03 populates source and delegation diagnostics only after connection authentication;
known and unknown source ids, with absent or invalid authentication, disclose no
stored fields. F-04 calls `authority_contract.envelope_problems` with the current
time and accepted membership/delegation state; expiry logic is not copied. The
stored source supplies its captured authority coordinates. Reading source evidence
does not execute the personal command or consume its nonce.

`K.select` now returns `ambiguous-channel-key` when more than one active key exists
for the channel; `revoked-key` remains the no-active-key case. The spec taxonomy
and `signing/ambiguous-channel-key` row cover the distinction. Both changed runtime
modules are byte-identical in `.veldo/` and `engine/.veldo/`.

All four original capsules were copied unmodified to `.capsule/` and replayed from
the repository root after the fixes. Each completed successfully, retained its valid
control, refused the attack, and printed no DEFECT marker. The directory was removed.
[review-capsules.json](review-capsules.json) retains their source digests and readable
outputs, including F-03's all-null diagnostic fields.

To repeat the original-code RED observations without changing this worktree's code:

```sh
git show 68ea1f3:.veldo/control_signer.py > /tmp/original-control_signer.py
python3 -B scripts/check_teeth_mutations.py --worker signing-ignore-personal-content --mutant /tmp/original-control_signer.py
```

The observer must list all four regression rows in `failed_rows`. The final suite
also includes the new key-taxonomy test, which uses the current key module.
No private keys, signatures, or encoded fixtures are retained in this proof.

The final targeted driver passed all 78 suite rows and rejected all 20 signing
mutations, including both variants for every finding. `mutations.json` records
the observations and the adjacent `.diff` files retain every applied change.
The driver timeout was increased to accommodate the eight additional full-suite
mutation runs; expectations and mutation acceptance rules are unchanged.
