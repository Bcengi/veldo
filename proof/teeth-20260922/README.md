# Teeth review, 2026-09-22

The three findings were completed separately on `teeth-20260922`:

| Finding | Commit | Change |
| --- | --- | --- |
| 1, VELDO-0107 | `1dd7fc0` | Suite 47 isolates signature coverage for every field. |
| 2, VELDO-0108 | `57ee29e` | Suite 48 compares raw stdout bytes on every refusal path. |
| 3, VELDO-0105 | `f264ba8` | Suite 44 exercises the declared absent-policy-line fallback. |

Production behavior did not need correction. No `.veldo/` file was changed, so there
are no changed runtime copies to mirror under `engine/.veldo/`. Work stayed on the
requested branch; nothing was pushed. Commits use only the configured author and
committer, with no trailers. Test commits are built in temporary repositories; no
new test pins an unlanded commit.

## Finding 1: signature coverage

New rows in suite 47 are `ipc/signature-fields-match-request` and
`ipc/signature-covers/<field>` for each of `schema`, `workspace`, `domain_uuid`,
`store_uuid`, `command`, `repository_uuid`, `repository_root_commit`, `clone_uuid`,
`binding_digest`, and `authority_generation`.

The field set is enumerated from the JSON emitted by `signed_bytes` and compared
with both `build_request` and `REQUEST_FIELDS`, excluding `signature`. Behavioral
rows iterate the union, so omission cannot silently remove a row. Each changes
one field of a signed request without re-signing, requires
`command_signature_invalid` and no application, then requires the identical
altered request to succeed when re-signed. The real judge uses a controlled
enrollment fixture; the schema row temporarily allows the altered schema. The
positive control proves that coordinate, identity, and shape checks cannot be
the reason for refusal in these rows. This isolates signature coverage, rather
than claiming another real-enrollment integration test. The affected signer
paragraph in `proof/VELDO-0107/README.md` now states these limits and observations.

## Finding 2: zero-byte stdout

Changed row `relay/an-unreachable-authority-is-reported-not-answered` now requires
raw stdout `== b""`, exit 3, the endpoint and failure diagnostic on stderr, and no
new application after stopping the real authority. Three new suite 48 rows assert
raw zero-byte output on the other refusal paths: `relay/usage-has-zero-stdout`,
`relay/oversized-request-has-zero-stdout`, and `relay/oversized-response-has-zero-stdout`.
They drive the executable relay; the response-size case uses a real socket. The
successful empty echo already compares raw bytes in `relay/the-authority-judges-not-the-relay`.

Each refusal path is mutated to emit `b"null"`, `b"\n"`, and `b" "`. The unavailable
path additionally emits `b"{}"`. Both `proof/VELDO-0108/README.md` and the finding 16
entry in `proof/fixes-20260922/README.md` distinguish the earlier empty-versus-object
repair from these raw-byte assertions and name the rows that now check zero bytes.

## Finding 3: the owner's start line

The changed suite 44 row `proofcheck/start-line-not-author-writable` retains the
supplied-policy precedence case and adds a policy with `required: true` and no
start line. An older bundle's manifest plants a real later commit in both
`from_commit` and `fix_validation.from_commit`. The row requires an empty recorded
line, `no start line recorded`, continued scope, and refusal for the missing
validation record. Reading the planted line would instead exempt the bundle.

The driver applies the declared top-level fallback, a nested-field fallback, and
manifest precedence. Each fails this same named row. AC3's set and the spec's prose
history now include the absent-line case; its owner-only claim, declared falsifier,
and shipped status are retained. The proof README describes the added evidence.

## Reproducible mutation results

Run `python3 scripts/check_teeth_mutations.py`, or select `--finding 1`, `2`, or `3`.
The script uses additive edits or exact replacements on temporary production
copies, preserving anchors needed by existing suite mutations. For each mutation
it runs the entire named suite in a worker, requires the baseline to have no failed
rows, requires every baseline row to remain present, and requires each target's
assertion to be false. A worker exception, timeout, exit failure, or missing target
is a driver failure, never evidence of detection.

All **29 mutations** were detected. Baseline suite-fragment counts were 23 for
suite 47, 8 for suite 48, and 8 for suite 44 (excluding shared preamble assertions).
The complete emitted results, including every red row, are in
[mutation-results.json](mutation-results.json). The table below names every mutation
and all rows it turned red; `covers/*` abbreviates `ipc/signature-covers/*`, and
`field-set` abbreviates `ipc/signature-fields-match-request`.

| Finding | Mutation | Rows whose assertions failed |
| --- | --- | --- |
| 1 | `command-only` | `field-set`, `covers/authority_generation`, `covers/binding_digest`, `covers/clone_uuid`, `covers/domain_uuid`, `covers/repository_root_commit`, `covers/repository_uuid`, `covers/schema`, `covers/store_uuid`, `covers/workspace` |
| 1 | `omit-schema` | `field-set`, `covers/schema` |
| 1 | `omit-workspace` | `field-set`, `covers/workspace` |
| 1 | `omit-domain_uuid` | `field-set`, `covers/domain_uuid` |
| 1 | `omit-store_uuid` | `field-set`, `covers/store_uuid` |
| 1 | `omit-command` | `field-set`, `covers/command` |
| 1 | `omit-repository_uuid` | `field-set`, `covers/repository_uuid` |
| 1 | `omit-repository_root_commit` | `field-set`, `covers/repository_root_commit` |
| 1 | `omit-clone_uuid` | `field-set`, `covers/clone_uuid` |
| 1 | `omit-binding_digest` | `field-set`, `covers/binding_digest` |
| 1 | `omit-authority_generation` | `field-set`, `covers/authority_generation` |
| 1 | `unsigned-request-field` | `field-set`, `covers/extra_coordinate` |
| 1 | `signed-nonrequest-field` | `field-set` |
| 2 | `unreachable-null` | `relay/an-unreachable-authority-is-reported-not-answered` |
| 2 | `unreachable-newline` | `relay/an-unreachable-authority-is-reported-not-answered` |
| 2 | `unreachable-space` | `relay/an-unreachable-authority-is-reported-not-answered` |
| 2 | `usage-null` | `relay/usage-has-zero-stdout` |
| 2 | `usage-newline` | `relay/usage-has-zero-stdout` |
| 2 | `usage-space` | `relay/usage-has-zero-stdout` |
| 2 | `oversized-request-null` | `relay/oversized-request-has-zero-stdout` |
| 2 | `oversized-request-newline` | `relay/oversized-request-has-zero-stdout` |
| 2 | `oversized-request-space` | `relay/oversized-request-has-zero-stdout` |
| 2 | `oversized-response-null` | `relay/oversized-response-has-zero-stdout` |
| 2 | `oversized-response-newline` | `relay/oversized-response-has-zero-stdout` |
| 2 | `oversized-response-space` | `relay/oversized-response-has-zero-stdout` |
| 2 | `unreachable-object` | `relay/an-unreachable-authority-is-reported-not-answered` |
| 3 | `manifest-fallback` | `proofcheck/start-line-not-author-writable` |
| 3 | `nested-manifest-fallback` | `proofcheck/start-line-not-author-writable` |
| 3 | `manifest-precedence` | `proofcheck/start-line-not-author-writable` |

The earlier driver, `python3 scripts/check_review_mutations.py`, also passed all
five cases: shallow negative ancestry (13), applying a bad-signature command (14),
relay JSON reserialization (15), unavailable relay output `{}` (16), and corrupting
last-seen state (17). Their exact mutations and red rows are preserved in
[earlier-mutation-results.json](earlier-mutation-results.json).

## Final gate

`bash scripts/verify.sh` exited 0 from the clean tree at
`f264ba8f0c56ec12aef1e0ec6907682537298db6`:

```text
selftest: 5563 passed, 0 failed
catalog: 8 run, 15 not-applicable (reasons on record), 0 waived, 0 undeclared
GATE: GREEN (f264ba8f0c56ec12aef1e0ec6907682537298db6)
```

First-use integration also passed after real spend writes in its temporary copy.
Lint, security, generated files, docs, packaging, template synchronization, and the
built-in contract checks passed. The final evidence commit adds this report and
the recorded mutation results; the gate result above identifies the tested code commit.

The gate began with `git status --porcelain` empty at `f264ba8`. Its two checkout-local
byproducts, `.veldo/last_verify` and `.veldo/events.jsonl`, were restored with
`git checkout -- .veldo/last_verify .veldo/events.jsonl` before the final evidence
commit. They are excluded from this work. The reviewer supplies the real gate stamp
from the checkout that verifies the merged tree. No independent approval is claimed.
