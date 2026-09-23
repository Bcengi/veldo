# VELDO-0064 proof

Release 1 revision 3 assignment inbox and Telegram projection. The specification status,
risk and `.veldo/policy.yaml` are unchanged. This proof is for independent review; it is not
a self-approval, and the canonical gate is run by the lead, not recorded here.

## What was built

`.veldo/control_assignment.py` is the one authoritative inbox. Person-required assignments are
`assignment` entities in the control store (`veldo.assignment/v1`: kind, owner, scope, deadline,
budget, brief, choices, subject, optional blocked unit, requester, request version, answer or
disposition). Every change is a signed command applied through `Inbox.apply`: the signature is
checked with `ssh-keygen -Y verify` against the signer's active key in the store's committed
keyring, stored membership decides who may act, and one registered store transaction
(`assignment_operation`) commits the change with the versions of every authority input it read.
Commands are `open`, `revise`, `answer`, `decline` and `cancel`. Answers walk the declared R18
edges `OFFERED -> ACCEPTED -> IN_PROGRESS -> SUBMITTED` through `entity_contract.transition`.

Opening an assignment tells the requester to stop (`stop_requester`). When the requester holds the
claim on the unit the assignment blocks, the same transaction releases it through
`control_claim.transition` (the claim organ's own release). A claim held by another principal is
refused as `not_owner`. `waiting_resources()` lists any claim still held on a pending
assignment's unit.

`index()` and `brief()` are the readers the later UI/API also uses. Both read one consistent
watermark, verify each row against its committed digest, and show an invalid record as
`category: invalid` with its problems and no content. Another repository's assignments are not
listed. `admit()` is the only answer to "may the blocked work proceed". It needs a valid
`SUBMITTED` record whose current version and digest were written by the owner's own journaled
answer command, and an owner who is still an active person member covering the scope.
Display fields such as `display_status` or `assignee` are never read.

`.veldo/control_channel_projection.py` projects pending entries to Telegram. It renders plain-text
presentation bytes from the brief (owner, scope, deadline, budget, subject, choices, brief) and
sends them with the Bot API `sendMessage` method over HTTP. It then commits one
`channel_projection` entity per (assignment, request version) holding the chat id, message id and
date the platform returned, the exact text, its digest, the assignment and request versions it
presented, and the configured chat address. A re-run sends nothing twice. A changed request
version sends a new message and keeps the old record. A platform refusal records nothing. A lost
answer is recorded as `unknown_outcome` with no message identity and is not sent blindly again.
The token is never stored or logged.

Both modules take the store, membership, claim and contract organs as arguments, so a copy loads
from any path. The inbox refuses a store module other than the one the claim organ commits
through. Canonical and installed copies are byte-identical; both are in `init_scaffold._FILES`
and not in `REQUIRED_SUBSTRATE`, because no validator loads them. Standard library only.

## Narrowest seams for dependencies not on main

- **Qualified Telegram edge (VELDO-0067, VELDO-0073) is not on main.** The projection talks to a
  Bot API origin: `https://` in production, or a loopback `http://127.0.0.1:` endpoint (the
  shape Telegram's own local Bot API server uses). The suite runs a loopback server that returns
  the platform's `sendMessage` answer, maps the configured `@veldo_owner` to a numeric chat id,
  and stores what it received so bytes can be retrieved. This is not live sandbox qualification.
  That remains VELDO-0066/0073 work, and no live network or real token was used.
- **Settlement and quorum (VELDO-0068) are not on main.** The inbox's `answer` command records the
  owner's signed answer so the answered state and admission can be exercised. It is not a
  presentation-bound settlement. `SATISFIED` is displayed as answered, but admission from it
  refuses as `missing_evidence` until its settlement consumer exists.
- **Worker adapters (VELDO-0039..0042, 0060/0061) are not on main.** The waiting worker is a real
  child process. It signs its own claim and open commands with its Ed25519 key over JSON lines,
  and exits only when the reply tells it to stop. It gets no database access.

Not implemented, by the specification's History: expiry sweeping, concurrent reassignment,
channel removal, lost-create-ack lookup and recovery (Release 2), extra channels (Release 4),
and Jira projection (dropped). `request.py`, `request_projection.py` and `request_doorbell.py`
(PLAN-0016 Jira surface) are unchanged.

## Criteria, rows and driven falsification

Suite: `scripts/suites/60_veldo_0064_inbox.py` (manifest name `60_veldo_0064_inbox`). The suite
runs over a real SQLite store with real OpenSSH signatures on every journal record and command,
the real claim receiver, a real child worker process and real HTTP. Registry:
`scripts/check_teeth_mutations.py`, finding 64. The footprint addition is recorded in the
specification's History. Every mutant finished its assertion run: no exception, hang or missing
row counts as a detection. The retained `.diff` beside this README is the exact applied change.

**AC1: the inbox exposes person-required assignments without holding a worker.**
Rows `VELDO-0064 inbox/waiting-resources` and `VELDO-0064 inbox/states-and-authority`.
The worker claims `unit-1` through the claim receiver, then opens a decision assignment. It
exits with code 0 when told to stop. The claim is released in the same journal record as the
assignment, the receiver has nothing pending, and `waiting_resources()` is empty. As additive
controls, a pending assignment over a held claim is reported, and a person cannot park another
principal's claim. The states row derives all eight schema states from `entity_contract`,
requires each to map to exactly one category, and drives pending, answered, declined and
canceled through real commands. It compares each entry's owner, scope, deadline, budget and
versions with the stored entity and current membership. It also checks the same four fields in
the bytes Telegram stored, and nine named refusals (stranger, agent, stale version, unoffered
ruling, forged signature, unknown unit, and others).

- `inbox-retain-claim-while-waiting` (the declared falsifier) skips the claim release.
  `inbox/waiting-resources` turns red: the claim stays owned, stays pending at the receiver and
  is listed by `waiting_resources`.
- `inbox-requester-keeps-waiting` replies `stop_requester: False`. `inbox/waiting-resources`
  turns red because the worker process is still waiting after 2 s. It is then killed.

**AC2: the Telegram projection keeps the actual message identity and request correlation.**
Row `VELDO-0064 projection/correlation`, plus `VELDO-0064 projection/send-outcomes`. Four pending
entries covering all three enabled kinds (`decision`, `review_disposition`, `acknowledgement`)
are sent once each. For every record, the chat id is the platform's numeric id (not the
configured `@veldo_owner`), the (chat, message) pair retrieves the platform's stored bytes, those
bytes equal the recorded text and digest, and the recorded request and entity versions equal
the inbox entry. A re-run sends nothing. A revision is a new message with a different id, and
the current record matches the new inbox version and the new deadline. The send-outcomes row
covers refusal, lost answer, no blind resend, token never recorded, metrics, and refusal of a
remote plain-HTTP origin.

- `projection-discard-message-id` (the declared falsifier) records `message_id=None`.
  `projection/correlation` turns red: no record retrieves platform bytes, and the two versions
  can no longer be told apart.
- `projection-configured-chat` records the configured `@veldo_owner` in place of the returned
  chat id. `projection/correlation` turns red.

**AC3: inbox views describe current assignments and do not grant authority.**
Rows `VELDO-0064 inbox/unauthorized-admission` and `VELDO-0064 inbox/visible-invalid`.
Admission is refused for a pending record carrying `display_status: assigned` and an `assignee`
(`not_answered`), and for an invalid record carrying the same labels (`invalid_record`). It is
also refused for a genuine owner answer copied onto another record by a service write
(`missing_authority`), for an answer whose owner's membership was then revoked
(`missing_authority`), and for declined, canceled, pending and absent assignments. The genuine
current owner answer is admitted, which is the positive control. For the readers: the revised
version reads as current accepted content equal to the store, and so does an unrevised pending
version. A record in a state outside the schema, an `assignment:` id of another kind, and a row
tampered outside the store are each listed as invalid with problems and no content, and their
briefs are visibly invalid. Another repository's assignment is not listed.

- `inbox-admit-displayed-assigned-status` (the declared falsifier) admits whenever
  `display_status` is `assigned`. `inbox/unauthorized-admission` turns red on both labelled
  records.
- `inbox-admit-without-journal-authority` drops the journal cross-check.
  `inbox/unauthorized-admission` turns red on the copied answer.
- `inbox-admit-ignores-owner-membership` skips the owner's current membership.
  `inbox/unauthorized-admission` turns red on the revoked owner's answer.
- `inbox-index-skips-invalid` drops invalid rows from the index. `inbox/visible-invalid` turns
  red for all three invalid records.
- `inbox-trust-tampered-content` drops the committed-digest check. `inbox/visible-invalid` turns
  red: the tampered row is shown as valid content.

`VELDO-0064 install/assets` checks scaffold registration, engine byte identity, installation by
the real `_lay` writer, and that sampled journal signatures verify with `ssh-keygen`.

Some mutants also turn `inbox/states-and-authority` red, because that row checks the same
Telegram bytes and released claims. `mutations.json` lists every red row and the suite's own
failing sub-check labels for each mutant, with source and mutant SHA-256. It also records
the unmutated baseline and one no-op copy per module; all of those stay green.

## Measurement

| Measurement | Result |
| --- | --- |
| Suite (`python3 -B scripts/selftest.py --suite 60_veldo_0064_inbox`) | about 1.25 s per run in the suite's own timer, 1.33 s wall including interpreter start, 33 passed, 0 failed |
| Serial driver: baseline, two no-op controls and all nine mutants | 18.4 s |
| `python3 -B scripts/check_teeth_mutations.py --finding 64` | 26.6 s wall, which reruns the honest baseline for every case; 9 mutations rejected |

All of these are well below the 60-second stop threshold. The slowest mutant is
`inbox-requester-keeps-waiting`, at 3.4 s including its 2 s wait.

Targeted checks run on this branch:

```text
python3 -B scripts/selftest.py --suite 60_veldo_0064_inbox  -> 33 passed, 0 failed
python3 -B scripts/check_teeth_mutations.py --finding 64    -> {"mutations_rejected": 9, "green_suites": {"60_veldo_0064_inbox.py": 33}}
python3 .veldo/validate.py all                              -> exit 0
bash scripts/check_generated.sh                             -> generated: pass
```

Reproduce the per-mutant observations with `python3 -B proof/VELDO-0064/drive.py`, which
rewrites `mutations.json`. No gate log, credentials, private keys, bytecode, encoded blobs or
gate stamps are committed.
