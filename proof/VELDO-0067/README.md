# VELDO-0067 proof

Release 1 revision 3: one restricted Telegram edge key enrolled under current authority, the
protected signer's answer purpose, and current edge and actor authorization at answer acceptance.
Specification status, risk and `.veldo/policy.yaml` are unchanged. This proof is for independent
review; it is not a self-approval, and the canonical gate is run by the lead, not recorded here.

Every answer runs against a loopback Bot API server (real HTTP, the platform's documented shapes),
not the Telegram service. Enrollment activates no ingress (VELDO-0073).

## What was built

- `.veldo/control_channel_enrollment.py`: `Enrollment.admit` takes the steward's OpenSSH-envelope
  signed `enroll_channel_edge` command (the authority contract's envelope and command digest, so the
  edge key, connection key, channel, edge principal and scope are all signed) and the edge key's own
  possession proof over that envelope in the `veldo-edge-possession` namespace. One transition writes
  the edge's service membership (no roles) and its key as the verification key at
  `authority_contract.CHANNELS['telegram_chat']['edge_key_id']`, which is what VELDO-0065 acceptance
  reads. `retire_channel_edge` records a retirement. Refusals are named with an error class;
  `metrics()` names the pending work (channels without a current edge key).
- `.veldo/control_signer_answers.py`: `control_signer` hands it every request from an identity that is
  an enrolled edge key. It authenticates the edge's connection key, then signs only a value with the
  canonical answer's exact fields, bound to undecided VELDO-0066 evidence, the one enrolled actor of
  that sender, the published presentation the evidence replies to, and a current delegation in every
  dimension. `EdgeSigner` is the edge side: VELDO-0066's `edge_sign` seam, unchanged Acquirer.
- `.veldo/control_keys_custody.py` (the earlier work in progress, kept as it was): a Landlock wrapper
  that stops a worker reading beneath a protected key directory. Verified on this host (Landlock ABI 8).
- All three in `init_scaffold._FILES` (not validator substrate); engine copies byte-identical.

## Rows, falsifiers and red record

Suite `scripts/suites/65_veldo_0067_edges.py`, 5.5 s. Real SQLite store, real OpenSSH signatures on
every command, journal record, possession proof and answer, the actual signer process, the actual
Acquirer and presenter, and a real worker process. Registry: `check_teeth_mutations.py --finding 67`
(footprint History line added). `python3 -B proof/VELDO-0067/drive.py` regenerates `mutations.json`
and the diffs: 18 mutants, each a wrong acceptance or a wrong signature on its named row, all by
assertion; baseline and a no-op copy of every mutated module green.

| Row | Criterion | Mutations (declared falsifier first) |
| --- | --- | --- |
| `install/assets` | all | `edge-enrollment-not-scaffolded`, `edge-custody-not-scaffolded` |
| `enrollment/schema-and-possession` | AC1 | `edge-possession-unchecked`, `edge-record-drops-connection-key` |
| `enrollment/binds-key-and-authority` | AC1 | `edge-digest-omits-public-key`, `edge-authority-from-envelope` |
| `enrollment/current-member-only` | AC1 | `edge-steward-role-unchecked`, `edge-key-in-use-unchecked` |
| `signer/purpose-refusal` | AC2 | `signer-signs-membership-command`, `signer-extra-fields-accepted` |
| `signer/delegation-dimensions` | AC2 | `signer-delegation-scope-unchecked`, `signer-presentation-not-from-evidence` |
| `signer/canonical-evidence` | AC2 | `signer-attribution-unbound`, `signer-decided-evidence-resigned` |
| `acceptance/current-edge-and-actor` | AC3 | `acceptance-retired-edge-current`, `retirement-dated-in-the-future` |
| `custody/worker-cannot-read-key` | AC3 | `custody-protected-directory-granted`, `custody-not-restricted` |

`edge-digest-omits-public-key` (in `authority_contract.py`) makes the steward's signature cover an
enrollment without its key, and the intruder's substituted key is enrolled. `signer-signs-membership-command`
signs an `enroll_principal` command handed over as the assertion. `acceptance-retired-edge-current`
(in the VELDO-0065 presenter) accepts the answer signed just before the edge key was retired.

**Red at 574ec36.** `python3 -B proof/VELDO-0067/drive.py --red 574ec36` runs the current suite
against that tree, extracted with `git archive` and unchanged: `red-at-574ec36.json`. All nine rows
red by their own assertions (119 failing checks), none raising. The suite drove the path that tree
has: the VELDO-0027 key registration accepted an edge key with no possession proof; the old signer
refused every answer (`forbidden-arbitrary-signing`), so no Telegram answer could be signed or
accepted; an unwrapped worker read the private key and hard-linked it out.

## Costs

Suite 5.5 s. Finding 67 with `--jobs 4`: 32 s. The drive (baseline, six no-op copies, 18 mutants,
serial): 138 s. Red run: 4 s. Both records were regenerated after merging origin/main at 36fd201
(VELDO-0040), whose three new `init_scaffold.py` lines shifted the two scaffold diffs.

## Known limits (not filed as tickets)

- The answer signature is in the authority contract's command namespace because that is what the
  VELDO-0065 acceptance verifies. It is safe because the signer signs only a value with the canonical
  answer's exact fields, which no command or envelope has; a separate namespace needs a presenter change.
- A VELDO-0025 delegation binds a request version and a presentation version but no request id. The
  signer binds the request through the presentation receipt the evidence replies to.
- The signer checks the actor's membership, not the VELDO-0026 revocation ledger; acceptance reads both.
- Custody is Linux only (it refuses to start a worker elsewhere), and it does not stop a worker that
  reaches an unconfined process of the owner's account. Placing the key directory is installation (W32).
