# VELDO-0073 proof

Per-channel live ingress activation of the Telegram edge. Specification status, risk and
`.veldo/policy.yaml` are unchanged (no policy change was needed). This proof is for independent
review; it is not a self-approval, and the canonical gate is run by the lead.

## What was built

- `.veldo/control_channel_activation.py` (engine copy identical, in `init_scaffold._FILES`, not
  substrate). The `channel_activation` record, written only by the owner's own signed
  `channel_activation_authorize` command (qualify, activate, stop), bound to his VELDO-0064 chat
  enrollment, the VELDO-0067 edge key, the Bot API origin and, when active, one committed
  `channel_qualification` record and the bot it proved. `Gate.admit` rereads the record at every
  exchange and refuses by name: `not_activated`, `edge_stopped`, `stale_configuration`, `stale_key`,
  `stale_enrollment`, `owner_not_current`, `qualification_expired`, `chat_not_enrolled`, and the
  proof's own reasons. `Gate.open` performs the exchange through its own transport and records it.
- The entry points (`ENTRY_POINTS`): `TelegramEdge.send`, `TelegramPresentationEdge.send`,
  `TelegramAcquisitionEdge` getMe and getUpdates, and the doorbell's `TelegramSink.send` all open
  through `control_channel_projection.gated_open`. With no gate only a loopback stand-in is reached;
  any other origin refuses as `not_activated` before a byte leaves. A getMe naming another bot than
  the activated one refuses.
- `.veldo/control_channel_ingress.py` (engine copy identical, scaffolded). `open_ingress` is the
  production construction from a 0600 host configuration: store, journal signer, host trust (its
  settlement signers), the VELDO-0067 protected answer signer and the token file, building the inbox,
  presenter, acquirer and the VELDO-0068 settlement service on one connection with gated edges.
  `Ingress.wake` digests whatever woke it, never reads it, acquires through getUpdates and runs
  settlement. The VELDO-0069 `decision_signer` comes from the configuration: its principal must be a
  host settlement signer and its 0600 key, outside the workspace, must sign a probe that verifies under
  those signers.

## How real evidence is told from fixture evidence

The gate's transport uses no proxy from the environment and, for https, a TLS context that loads only
the trust store compiled into the host's OpenSSL (never `SSL_CERT_FILE` or `SSL_CERT_DIR`), requires
a certificate and checks the host name. Each exchange records its origin, host, status, the digest of
the answer bytes, the identities in the answer, and for TLS the verified peer's certificate
fingerprint, names, issuer and protocol. `qualification_problems(record, TELEGRAM_ORIGIN)` accepts
only a record whose every exchange was made with `api.telegram.org` over such a session whose
certificate names that host, whose presentation message ids are the ones sendMessage returned to the
enrolled chat, whose owner answer evidence is the bytes of a recorded getUpdates answer, whose sender
is the enrolled owner replying to the presentation, whose unenrolled sender was refused, and whose
settlement is that answer's. A loopback stand-in exchange carries no TLS peer, so fixture evidence
never qualifies the Telegram origin. A stand-in origin can be qualified and activated (that is how the
suite drives the gate), but that activation cannot admit any other origin.

What this cannot prove: Telegram does not sign its answers, so a record is trusted as the store is
(the threat model trusts the store, the signer and the token's custody). In a factory the witness beside
it is the owner's activation over the record's digest, signed with his enrolled key after he saw the
message on his phone; that is VELDO-0138's real-factory qualification. A record copied into a file
proves nothing by itself: anyone can write one (the second critical review forged one that the
consistency row accepted).

## Rows, falsifiers and red record

Suite `scripts/suites/70_veldo_0073_activation.py` (about 3 s; stage environment green): real SQLite
store, OpenSSH signatures, the actual protected signer process, the production ingress construction,
two loopback Bot API servers, a local TLS stand-in, and a socket guard that refuses and counts every
connection beyond 127.0.0.1, so no row and no mutant reaches Telegram. Registry:
`scripts/check_teeth_mutations.py --finding 73`. `python3 -B proof/VELDO-0073/drive.py` regenerates
`mutations.json` and the diffs: 24 mutants, each reds its named row by assertion, baseline and a no-op
copy of each mutated module green. `red-at-3dc0393.json`: the current suite against the
pre-change tree, every row red by assertion. `red-at-ad856ac.json`: the current suite against the tree
before review 1's redirect fix, where `activation/no-redirect` is the one red row, by assertion.
`red-at-792c494.json`: the same against the tree before review 2's origin parsing, where
`activation/no-redirect` is again the one red row, by assertion.

| Row | Criterion | Mutations (declared falsifier first) |
| --- | --- | --- |
| `install/assets` | all | `activation-not-scaffolded` |
| `entry-points/enumerated` | AC1 | `presentation-edge-bypasses-gate`, `entry-point-unlisted` |
| `activation/no-implicit` | AC1 | `doorbell-token-resolves-sends`, `ungated-edge-reaches-any-origin` |
| `activation/explicit-bound-operates` | AC1 | `steward-authorizes-owner-edge`, `send-to-any-chat`, `production-acquisition-ungated` |
| `qualification/real-platform-proof` | AC2 | `fixture-evidence-accepted`, `tls-host-unchecked`, `trust-store-from-environment`, `answer-not-the-platform-bytes` |
| `settlement/production-construction` | AC2 | `host-trust-optional`, `decision-key-unverified` |
| `notification/wakes-only` | AC3 | `notification-settles` |
| `stop/halts-edge` | AC4 | `stop-ignored` |
| `stale/key-and-configuration` | AC4 | `bindings-not-compared`, `origin-unbound`, `bot-unbound` |
| `activation/no-redirect` | AC1 (reviews 1 and 2) | `redirect-followed`, `ungated-edge-default-opener`, `gate-opener-own-build`, `stand-in-prefix-match`, `https-origin-unparsed` |

`qualification/live-record-consistent` checks only that `proof/VELDO-0073/live/qualification.json`,
once the live run writes it, is complete for the Telegram origin, matches its digest and carries
nothing token-shaped. It is NOT proof of AC2's real-platform leg, because a file cannot show where
it came from. The live run's witness is the owner: the record names his reply's message id and date,
which he can confirm on his phone. The binding proof is the running factory's own qualification and
activation under VELDO-0138, where the gate records every exchange in the factory's store and his
enrolled key signs the activation over it.

## The live run (the lead, once, with the owner)

    python3 -B proof/VELDO-0073/qualify_live.py --token-file /abs/path/bot-token --owner-chat <his user id>

The token file must be the account's own 0600 file; the token is never printed, logged or written
(the run's private 0600 copy is unlinked at exit). The runner builds a fresh authority, constructs the
ingress with `open_ingress`, records the owner-signed qualification run, sends ONE decision to his chat,
waits (default 600 s) for his reply to that message (`accept: <reason>`), settles it, acquires one
update from an unenrolled sender id from a loopback stand-in (Telegram 29047), records the
qualification, activates, asks the gate, stops the edge, and writes `live/qualification.json`.
`--rehearse --out <dir>` runs the same steps against a loopback stand-in and contacts nothing; it was
run once here and its stand-in record is refused by the live row, as it should be.

## Known limits

- The scratch authority's owner key signs the activation commands in the live run; the owner's own
  consent for the run is Telegram 29081. A production authority would take his enrolled key.
- `open_ingress` is the production construction; wiring it into the authority service's serve loop
  is not in this footprint.
- The decision signer signs in the ingress process with the host's configured key; the protected
  signer process has no decision purpose that judges the binding body before signing (not in this
  footprint; control_signer.py would gain it).
