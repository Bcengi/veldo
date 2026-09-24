# VELDO-0068 proof

Release 1 revision 3: one settlement per request version, carrying the offered choice, its ruling and
the owner's own reasoning; the settlement, its nonce, the typed effect, the terminal request state and
the receipt in one store transaction; and conjunctive journey and request authority. Specification
status, risk and `.veldo/policy.yaml` are unchanged. This proof is for independent review; it is not a
self-approval, and the canonical gate is run by the lead, not recorded here.

Every Telegram answer runs against a loopback Bot API server (real HTTP, the platform's documented
shapes), not the Telegram service.

## What was built

`.veldo/control_request_settlement.py` (engine copy byte-identical, in `init_scaffold._FILES`, not in
`REQUIRED_SUBSTRATE`). Standard library only. Nothing else in the engine changed.

- **Journey configuration.** `JOURNEY` names the five enabled touchpoints (grooming, admission, priority,
  finding disposition, decision disposition): the inbox kind each is presented as, its roles, count and
  independence, and the typed effect of each ruling.
- **Terms.** The requester signs `settlement_terms` (touchpoint, target, proposal, the request's own
  `required_roles` and `quorum`) and opens the VELDO-0064 assignment with the terms as its subject, so the
  VELDO-0065 presentation binds the terms digest.
- **Answers.** Telegram answers are the presenter's accepted `presentation_answer` records (VELDO-0066
  attribution, VELDO-0067 edge signature), unchanged. `api_answer` accepts an answer signed by the
  configured API edge under the same presentation rules (current head, current bindings, the owner only).
- **Settlement.** `settle` reads every accepted answer of the version in acceptance order; the earliest
  one that still binds the current presentation wins and every other is named on the settlement, never
  counted. The requirement is policy AND terms (union of roles, larger count and independence), decided
  by `authority_contract.authorize` per scope, by distinct principal, with the requester never counted as
  independent. A count above one or an independence above one blocks as `unsupported_quorum`. One
  registered transaction writes the settlement, the effect, the receipt and the assignment moved to
  SATISFIED with the answer and the settlement reference, keyed and nonced by request and version.
- **Publication.** `publish` records the settled requests as statuses of a VELDO-0035 accepted revision
  (`.veldo/settlements/<alias>.json`, `<alias>.request.json`) on a publication connection, accepts its
  snapshot and materializes it; `published_state` reads request state from those statuses only.
- **One authority.** The service refuses any connection other than the one its inbox and presenter use.
  The PLAN-0016 `FilesystemSettlementStore` is not loaded, enrolled or changed.

## Rows, falsifiers and red record

Suite `scripts/suites/69_veldo_0068_settlement.py` (6 to 7 s): real SQLite store, real OpenSSH signatures
on every command, journal record, possession proof, edge and API answer, the actual protected signer
process, Acquirer and presenter, two concurrent writers on two connections, a real Git repository with
a VELDO-0035 revision and snapshot, and a reader in another process. Registry:
`scripts/check_teeth_mutations.py --finding 68` (footprint History line added).
`python3 -B proof/VELDO-0068/drive.py` regenerates `mutations.json` and the diffs: 17 mutants, each reds
its named row by assertion (no section raised), baseline and a no-op copy of both mutated modules green.

| Row | Criterion | Mutations (declared falsifier first) |
| --- | --- | --- |
| `install/assets` | all | `settlement-not-scaffolded`, `settlement-claimed-as-substrate` |
| `ruling/offered-choice-and-reasoning` | AC1 | `chosen-option-generic`, `effect-type-ignores-ruling` |
| `settlement/one-winner` | AC2 | `latest-answer-wins`, `conflicting-answer-unrecorded` |
| `settlement/one-transaction` | AC2 | `receipt-separate-transaction`, `settlement-nonce-per-answer` |
| `terminal/materialized-settlement` | AC3 | `request-left-open`, `closed-request-answered-by-api` |
| `authority/roles-and-independence` | AC4 | `request-roles-ignored`, `policy-roles-ignored`, `requester-separation-ignored` |
| `authority/owner-and-presentation` | AC4 | `api-answer-owner-unchecked`, `api-edge-signature-unchecked` |
| `authority/unsupported-quorum-blocks` | AC4 | `request-quorum-weakened`, `independence-above-one-accepted` |

AC1 answers all five touchpoints with all three offered choices (15 signed Telegram replies, admission's
typed in capitals) and compares the platform message, the settlement and the effect. AC2's conflict pair
is a Telegram accept then an API reject, and then two API answers racing on two connections.
`receipt-separate-transaction` commits the receipt by a second command after the terminal one. AC3 reads
the published snapshot in a child process beside the repository's stale `status: open` request records.
`request-roles-ignored` settles a grooming request whose terms ask for a role the owner lacks.

**Red at 335d996.** `python3 -B proof/VELDO-0068/drive.py --red 335d996` runs the current suite against
that tree, extracted with `git archive` and unchanged: `red-at-335d996.json`. All eight rows red by their
own assertions (118 failing checks), none raising. The module does not exist there, so the answers are
recorded by the presenter and nothing settles them.

## Costs and stage environment

Suite 6 to 7 s. Finding 68 with `--jobs 4`: 33 s. The drive (baseline, two no-op copies, 17 mutants,
serial): 150 s. Red run: 5 s. Under the gate's stage environment (`env -i`, a short `/dev/shm` HOME and
TMPDIR, C.UTF-8, UTC, hash seed 0, no user site, Git system and global configuration off) the suite
passed (8 rows, exit 2 as the partial-run marker) and finding 68 rejected all 17 mutations (exit 0).

## Known limits (not filed as tickets)

- The answer is accepted evidence in its own transaction (VELDO-0065's, with its own nonce) before the
  settlement transaction. A stop between the two leaves an accepted, unsettled answer, shown as pending
  work by `metrics()`; the next `run()` settles it. Recovery beyond that is Release 2.
- The inbox's `admit` and `resume` do not read a SATISFIED assignment (it refuses as missing evidence,
  as VELDO-0064 states), so a unit parked on a settled request is not resumed here; the typed effects are
  the obligations VELDO-0069 consumes.
- The presentation shows the terms by kind, reference and digest only, not their required roles.
- Only the presented owner can answer, so a count above one is unsupported in Release 1 (Release 3).
- The API answer is verified as a signed request from the configured API edge principal, as VELDO-0126
  does; the VELDO-0130 server itself is not part of this change.
