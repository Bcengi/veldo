# VELDO-0126 proof

One intake for owner messages from Telegram and the authenticated API, PLAN-0019 revision 3 W89.
Branch `build-veldo-0126`, built on c3c340e with origin/main merged (d34980f). The specification
status, risk and `.veldo/policy.yaml` are unchanged. This is implementation evidence, not
independent review, owner approval or a full-gate result; the lead runs `bash scripts/verify.sh`.

## What landed

`.veldo/control_intake.py` (engine copy byte-identical, in `init_scaffold._FILES`, not in
`REQUIRED_SUBSTRATE`). Standard library only.

- **Two sources, one command.** `Intake.receive(source_kind, payload)` accepts exactly
  `telegram_message` (the id of kept VELDO-0066 evidence) and `api_request` ({request, signature});
  anything else is refused `unsupported_source`. Each adapter builds the same normalized command
  (source kind and id, exact text, principal, requested project, the proposal it clarifies, and the
  source's provenance) and hands it to one common service, whose store command `intake_record` is
  the only writer of intake sources, proposals and questions (`control_store.declare_owners`).
- **Who is speaking.** A Telegram message is attributed again from its kept evidence by the
  VELDO-0066 Acquirer, by stable sender id only; only an ordinary message (no reply, or a reply to a
  message that is not a presentation) is intake, and a presentation answer is settlement's. An API
  request must be signed by the configured API edge service principal with its active keyring key,
  and the principal it names must be an active person member. Both sources pass the Acquirer's person
  check inside the store transaction.
- **Project context.** Candidates are the served projects the principal's membership scope covers.
  The project is the one the API request names, else the one candidate the text names, else the only
  candidate. Otherwise intake keeps an inbox proposal and a question: on Telegram it is sent through
  the VELDO-0065 edge as a reply to the message and its platform id recorded; on the API it is the
  response. A follow-up (a Telegram reply to the message or the question, or an API request naming the
  proposal) is kept with its own source, and resolves an inbox proposal only when it names one of the
  question's candidates.
- **Proposals only.** Intake writes intake sources, proposals (PROPOSED, AWAITING_PROJECT, RESOLVED)
  and questions, never a unit, backlog item, admission, priority, claim, reservation or effect.
- **One request, one proposal.** The same source identity with the same content returns the recorded
  proposal and writes nothing; changed content, a Telegram edit included, is `identity_conflict`.

**The API leg.** AC1's API leg runs through `Intake.receive('api_request', ...)`, the interface the
authenticated API will call, driven with requests the API edge signs with a real OpenSSH key. The API
server is VELDO-0130, not built yet; **VELDO-0130 drives its own leg over its server when it is
built.** The authority service (VELDO-0047) does not route intake commands yet: intake verifies the
API edge exactly as the service's command check does (active member, active keyring key, OpenSSH
verification), in process on the real store.

## Rows, falsifiers and red record

Suite `scripts/suites/68_veldo_0126_intake.py` (1.1 s; 18 rows, 44 assertions with the preamble):
real SQLite store, OpenSSH journal, edge and API signatures, the production Acquirer and
TelegramAcquisitionEdge over a loopback Bot API (real HTTP, no Telegram service), and a loopback
ticket host that records every request. Registry: `scripts/check_teeth_mutations.py --finding 126`.
`python3 -B proof/VELDO-0126/drive.py` writes `mutations.json` and the diffs: 14 mutants, each reds
its named row by assertion, no region raised, baseline and no-op copy green, 19.2 s serial.

| Row | AC | Mutations (declared falsifier first) |
| --- | --- | --- |
| `intake/common-command` | AC1 | `api-into-separate-queue`, `api-principal-from-edge` |
| `intake/unresolved-project-asks` | AC1 | `unresolved-first-candidate-wins`, `question-not-sent` |
| `intake/plain-objective` | AC2 | `ticket-id-required`, `text-trimmed` |
| `intake/follow-up-clarification` | AC2 | `follow-up-as-new-objective`, `clarification-replaces-objective-text` |
| `intake/authenticated-sources-only` | AC3 | `api-signature-unchecked`, `unsupported-source-rides-api` |
| `intake/no-admission` | AC3 | `accepted-message-creates-unit`, `accepted-message-prioritized` |
| `intake/same-request-same-proposal` | AC3 | `changed-content-overwrites`, `repeat-refused-as-conflict` |

`intake/observations` (identities, versions, trace, taxonomy class, counts and pending work equal to
the store) and `install/assets` have no mutation; nine `ran/` rows say each region ran to its end.

**Red at d34980f.** `python3 -B proof/VELDO-0126/drive.py --red d34980f` runs the current suite
against that tree, unchanged: `red-at-d34980f.json`. The intake module does not exist there, so the
suite uses a stand-in that takes nothing. All eight criterion and observation rows and
`install/assets` are red by their own assertions; all nine `ran/` rows pass; nothing raised.

**Stage environment.** The suite and `check_teeth_mutations.py --finding 126 --jobs 4` were run once
under the gate's `env -i` stage environment (PATH, HOME and TMPDIR a new /dev/shm directory holding a
python3 symlink): 18 rows green, 14 mutations rejected.

## Known limits (not filed as tickets)

- Every `take_telegram` pass re-attributes every kept non-answer update, so a refused update is
  counted again on each pass; evidence, questions and proposals are found by scanning one kind.
- A question whose Telegram send fails stays open and undelivered, by name; resending is Release 2.
