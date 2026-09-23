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

Final review-fix acceptance ran from a clean tree at `89cc28ebab0ca8d83696811e1ff7ff1da5a53f24`:

```text
selftest: 5658 passed, 0 failed
mutations: passed registered=74 executed=74 rejected=74 workers=96 elapsed=41.945s
catalog: 8 run, 15 not-applicable (reasons on record), 0 waived, 0 undeclared
GATE: GREEN (89cc28ebab0ca8d83696811e1ff7ff1da5a53f24)
```

The gate completed in 654.973 seconds. Its mutation stage includes fresh baseline,
no-op, and defective-copy controls. [review-gate-run.json](review-gate-run.json)
records the clean-tree precondition and exit status; [gate-summary.json](gate-summary.json)
retains the log digest and all signing mutation observations. The final evidence
commit changes proof only. The checkout's `.veldo/last_verify` and
`.veldo/events.jsonl` are restored before that commit and are not included.

## Follow-up F-05: bind every decision field

The new rows were run against the unmodified signer from `f95c7a6` before
implementation. Relabeling only the presentation digest, assertion kind or scope
was accepted; all three refusal rows were RED. Missing signed digest, kind, scope
and version fields were also accepted. The contract now owns the decision field
set, including request and presentation versions, and the signer requires explicit,
equal values in the personal parameters and payload. Both kinds and scopes in the
relabel cases are delegated, so delegation checks cannot mask this regression.
The runtime modules are mirrored byte-for-byte into `engine/.veldo/`.

[followup-f05.json](followup-f05.json) records the RED rows, the targeted green
development run (88 signing rows), and baseline/no-op/mutant observations for
`signing-bind-only-original-fields` (reintroduces F-05) and
`signing-default-missing-personal-fields` (defaults an omitted signed field).
Both mutations fail their named rows; their applied diffs are adjacent. These
development checks are not a gate or a landing approval.

## Follow-up F-06: compare against this authority

Before the fix, the unmodified `f95c7a6` signer accepted personally signed commands
for another store, domain and repository, each changed independently. Each source
was captured in this store, each Ed25519 signature verified, and the authority
contract rejected exactly the foreign coordinate. Those three signer refusal rows
were RED, as were missing authority configuration cases.

The signer's trusted configuration now supplies `authority_ids`, containing
`domain_uuid`, `repository_uuid` and `store_uuid`. All three must be nonempty
strings. The signer combines these coordinates with current accepted membership
and delegation versions, as `control_keys.admit` does, and passes them to
`AC.envelope_problems`. It never derives authority coordinates from the envelope.
Missing configuration refuses; reading evidence still does not execute a command
or consume its nonce. The signer and its engine mirror are byte-identical.

[followup-f06.json](followup-f06.json) records RED and targeted green observations
(95 signing rows), plus baseline/no-op/mutant results for
`signing-copy-envelope-coordinates` (reintroduces F-06) and
`signing-ignore-coordinate-problems` (discards only coordinate refusals). Both
mutations are caught by their named rows; the exact applied diffs are adjacent.

All four earlier capsules were replayed. The original F-02 and F-03 scripts pass
unchanged with their controls and attacks intact. Original F-01 and F-04 fixtures
omit newly mandatory signed parameters and authority configuration, so they now
stop at their positive controls. A second replay supplies those required inputs;
F-01's parameter assignment becomes an update so its rejection retains the other
signed fields. All four compatible replays pass their controls and refuse their
attacks with no DEFECT marker. No attack or assertion was removed or weakened.
[followup-capsules.json](followup-capsules.json) records both runs and source hashes;
[followup-capsule-compatibility.diff](followup-capsule-compatibility.diff) records
the exact fixture changes. No private keys or signatures are retained.

## F-05 and F-06 clean-tree acceptance

The canonical gate was run from a clean tree at `7498864958570e3ac6363c79cba9a22d359bed71`:

```text
selftest: 5675 passed, 0 failed
mutations: passed registered=78 executed=78 rejected=78 workers=100 elapsed=50.574s
catalog: 8 run, 15 not-applicable (reasons on record), 0 waived, 0 undeclared
GATE: GREEN (7498864958570e3ac6363c79cba9a22d359bed71)
```

The run took 661.290 seconds. All 95 signing rows and all 24 signing
mutations were exercised, including both variants of F-05 and F-06 and the
earlier F-01 through F-04 mutations. Fresh baselines and no-op copies passed.
[followup-gate-run.json](followup-gate-run.json) records the clean precondition,
commit, exit code and duration. [gate-summary.json](gate-summary.json) and
[mutations.json](mutations.json) retain the gate observations; [observations.json](observations.json)
contains the 95 signing rows observed by the gate. The final commit changes proof
only; `.veldo/last_verify` and `.veldo/events.jsonl` are restored and excluded.

To reproduce the new RED rows without changing runtime files in this checkout:

```sh
git show f95c7a6:.veldo/control_signer.py > /tmp/f95c7a6-control_signer.py
python3 -B scripts/check_teeth_mutations.py --worker signing-ignore-personal-content --mutant /tmp/f95c7a6-control_signer.py
```

The observer reports the three isolated F-05 relabel rows and all three F-06
foreign-coordinate rows in `failed_rows`, as well as missing-input refusal rows.
The worker exit status is not its assertion verdict; inspect `failed_rows`.
