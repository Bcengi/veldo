# VELDO-0069 proof

Release 1 revision 3: a current settlement of a governing decision question writes its exact governing
binding in the settlement's own transaction, and only that binding makes the governed work eligible.
Specification status, risk and `.veldo/policy.yaml` are unchanged. This proof is for independent review;
it is not a self-approval, and the canonical gate is run by the lead, not recorded here.

Every Telegram answer runs against a loopback Bot API server (real HTTP, the platform's documented
shapes), not the Telegram service.

## What was built

One production module changed: `.veldo/control_request_settlement.py` (engine copy byte-identical,
already in `init_scaffold._FILES`). The VELDO-0054 consumers (`plan.py`, `control_eligibility.py`,
`control_decision_dependency.py`) needed no change and are unchanged.

- **The question.** Terms whose target kind is `governing_decision` (accepted only on the
  decision_disposition touchpoint) name the governing record and the exact question: decision id,
  revision, framing digest, subject (kind, id, digest) and scope digest, with the digest of that
  question. `governing_target(record_id, record)` builds it. A subject kind other than spec or plan is
  refused at the terms as `unsupported_subject`.
- **The binding.** Settling such a request adds a `decision_settlement` record, keyed by the record and
  the revision ruled on, to the one VELDO-0068 transaction (settlement, effect, receipt, terminal
  request). It carries the chosen option, the decider, the time, links to the settlement and receipt,
  and a body in the VELDO-0054 signed shape signed by the service's new `decision_signer` (principal,
  sign) under `veldo-decision-settlement`. The body is the question the owner was shown, never the
  record at settlement, so a stale framing, another subject or an older revision is bound faithfully and
  the consumers name it. The kind is owned by the settlement command.
- **Stops.** A record whose governed subject kind is unsupported (`unsupported_subject`), a question
  naming no recorded governing decision (`missing_decision`) and a service with no decision signer
  (`unavailable_service`) refuse before anything is written: no receipt without its binding.
- **Future revision.** A question at a revision above the record's current one, as read and pinned in the
  settling transaction, is refused as `future_revision` (class stale_subject) with nothing written, so a
  binding never exists for a revision nobody was shown. The terms are not checked against the record:
  they read no governing record, and settlement is the one place that reads it pinned.
- **Supersession.** Consumers read only the binding of the record's current revision, so a question at
  a later revision supersedes an earlier binding; one revision is bound once (`already_settled`).
- **Observability.** The settle observation carries the binding id, the record, whether the binding is
  current and the named blockers it will raise; `metrics()` counts bindings. No signature or reasoning
  text is observed.

## Rows, falsifiers and red record

Suite `scripts/suites/70_veldo_0069_bindings.py` (about 4 s): real SQLite store, real OpenSSH signatures
on every command, journal record, possession proof, edge assertion and binding body, the actual protected
signer process, Acquirer, presenter and settlement service, the Gate, plan, frontier and run lens over a
real Git checkout, and a reader in another process. It also passes in the stage environment
(`env -i`, empty HOME, `GIT_CONFIG_GLOBAL=/dev/null`).

`red-at-25703ef.json`: the current suite against the pre-change tree (`git archive 25703ef`): all seven
rows red, by assertion (no section raised).

`red-at-5596c04.json`: the current suite against the tree the review read (`git archive 5596c04`):
`refusal/future-revision` red by assertion, the future question settled and its early binding then cleared
the work and refused the genuine question as already_settled. `binding/owner-ruling` is green there: that
tree already signed the owner's ruling, and the row's teeth are `ruling-forced-approve`.

`python3 -B proof/VELDO-0069/drive.py` regenerates `mutations.json` and the diffs: 13 mutants, each reds
its named row by assertion, baseline and a no-op copy of each of the three mutated modules green.
Registry: `scripts/check_teeth_mutations.py --finding 69`.

| Row | Criterion | Mutations (declared falsifier first) |
| --- | --- | --- |
| `binding/one-transaction` | AC1 | `binding-skipped-without-signer` |
| `binding/owner-ruling` | AC1 | `ruling-forced-approve`, `binding-choice-forced-accept` |
| `eligibility/resolved-request` | AC1 | `receipt-without-binding` |
| `refusal/wrong-framing` | AC2 | `binding-framing-from-record` |
| `refusal/wrong-subject` | AC2 | `binding-ignores-subject-digest` |
| `refusal/wrong-version` | AC2 | `binding-revision-from-record` |
| `refusal/unsupported-subject-stops` | threat model | `unsupported-subject-bound`, `unsupported-subject-terms-accepted` |
| `refusal/future-revision` | threat model | `future-revision-accepted` |
| `consumers/inline-bypass` | AC3 | `inline-status-authority`, `inline-status-authority-at-stations`, `record-status-authority` |

## Known limits

Out of review scope per the specification: commit barrier crashes, concurrent and restart matrices
(Release 2); expiry, reopening, tripwires and reverse invalidation (Release 3); forged rows in the store.
The framing digest is the one the requester's terms carry; linking it to the presented brief is not in
this slice. No production construction wires a `decision_signer` yet: whoever constructs the settlement
service passes it, and the host lists that principal in its settlement signers.
