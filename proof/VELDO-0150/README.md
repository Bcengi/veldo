# VELDO-0150 proof: an objective from the project owner's own message is accepted by that message

Release 1 stage 4 of PLAN-0019 revision 4 (W110). The owner's own authenticated message, on Telegram or
through the API intake, accepts the objective it proposed with nothing presented; an objective from
anyone else is still presented and accepted only by his answer, as VELDO-0077 built it. VELDO-0077's
specification text, criteria and checks are unchanged. Specification status, risk and
`.veldo/policy.yaml` are unchanged. This proof is for independent review; it is not a self-approval,
and the canonical gate is run by the lead, not recorded here.

## The design as built

**One new operation, `accept_message`, in `.veldo/control_objective.py`.** It is the second acceptance
path beside `accept` (the VELDO-0068 settlement of a presented request), and it touches neither that
path nor any VELDO-0077 check. The PM, or any member in the project's scope, sends it as a signed
command naming the objective, its current version, the revision and bound digest it accepts, and the
intake command it names as evidence.

**The evidence is the message's own intake command.** Inside the store transaction the service finds
the one intake source whose recorded result is the objective's intake proposal (`proposing_source`: the
message that proposed it, or the follow-up that resolved an inbox proposal into it; a clarification is
not one). The intake command is the journal record that first wrote that source (`first_writer`,
assigned by the store inside the writing transaction; intake sources are written only by VELDO-0126's
`intake_record`). A command naming any other intake command is refused `invalid_input:intake_command`.

**Only the project's owner's own message counts.** The source's principal, the proposal's principal and
the bound acceptor must all be the project's owner, who must be a current person member holding
`project_owner` (the same owner check `accept` makes); otherwise `not_owner:source`. That is also the
answer for his message in a project he does not own: the objective's acceptor is that project's owner,
and his message is not that owner's. The command must name the objective's current revision and bound
digest, or it is refused `stale_subject:revision`. A paused or closed project refuses
`project_not_active:<state>`, as it does `accept` (no row here drives that refusal).

**What the acceptance binds.** The record moves PROPOSED to ACCEPTED through `entity_contract.transition`
and records `accepted_revision`, and an `acceptance` with `path: own_message`, the intake command and
its journal sequence, the intake source, source kind and id, content digest, the proposal, the ruling
`approve`, the owner as its one principal, the revision and the bound digest: the same binding fields
an accepted answer records. It also records the canonical attribution of the message
(`attribution`): for Telegram, re-read from the kept VELDO-0066 evidence the source names (bot, chat,
message id, sender id, platform date, update id, evidence id and digest, which must match what intake
recorded, `missing_evidence:attribution` otherwise); for the API, the edge-signed request's id, edge,
principal and digest. The history entry names the intake command.

**A repeat is the same acceptance.** The same `accept_message` again, naming the intake command the
objective was accepted by, returns the recorded acceptance and writes nothing, before the version check,
so a repeat made from an earlier read still answers. A repeated message never reaches it twice: intake
returns the same proposal for the same source, and a second `propose` from it is `already_exists`.

**Acceptance admits nothing.** A feature proposed under an objective his message accepted is RAW with
no admission and no priority, as under any accepted objective (VELDO-0077 AC1). Admission by the same
message is VELDO-0079's amendment and is not built here.

**Observability.** Each accept or accept_message observation carries `acceptance`: the path, and for
his own message the intake command, source, revision and bound digest, for his answer the request and
settlement. `metrics()` gains `acceptances`: accepted by his own message, accepted by answer, and
own-message acceptances refused. `_acceptance_seq`, which dates the acceptance for evidence freshness
in `assess`, reads both paths.

Not changed, filed for its owner: the VELDO-0128 Telegram report (`control_telegram_report._objective`)
names an accepted objective's evidence as its settlement and receipt, which print as unavailable for
an acceptance by his own message. It is outside this footprint.

## Suite

`scripts/suites/75_veldo_0150_own_message_acceptance.py`
(`python3 scripts/selftest.py --suite 75_veldo_0150_own_message_acceptance`, about 1.3 s). The real SQLite
store with OpenSSH command, journal, edge and API signatures; people enrolled by the steward's signed
VELDO-0025 commands and the Telegram edge by his VELDO-0067 enrollment; Telegram messages acquired by
the production VELDO-0066 Acquirer over a loopback Bot API (getMe, getUpdates, sendMessage over real
HTTP, no network, no real token) and taken by `Intake.take_telegram`; API messages through
`Intake.receive('api_request', ...)` as requests the API edge signs, as VELDO-0126 drives its API leg;
projects activated by their owners' signed VELDO-0076 commands; any other objective presented as a
VELDO-0064 request by the VELDO-0065 presenter, answered through the API edge and settled by the
VELDO-0068 settlement. Expected values come from outside the objective service: the intake command
from the suite's own SQL over the journal, cross-checked against intake's own command id; the
attribution from the message the loopback platform sent; the bound digest recomputed with hashlib.
Each row is reported once, and every row fails by assertion.

| Criterion | Rows |
|---|---|
| AC1 | `own-message/telegram`, `own-message/api`, `own-message/non-owner-presented` (declared falsifier), `own-message/admits-nothing` |
| AC2 | `evidence/bound-intake-command` (declared falsifier), `evidence/same-bound-fields`, `evidence/project-not-his`, `evidence/repeat`, `evidence/stale-revision` |

`own-message/telegram` and `own-message/api`: olga, the owner of proj-a, writes on Telegram and through
the API; each becomes a proposed objective of proj-a, the PM proposes it, and her message accepts it
with no request opened, no record other than the objective naming it and nothing sent; the acceptance,
the observation and the metrics name the path and the intake command. `own-message/non-owner-presented`:
zed (a member of proj-a who owns proj-c) on Telegram and asha through the API; each objective's
own-message acceptance is refused `not_owner:source` writing nothing, and each is presented to olga;
an answer to revision 1 after an amendment is refused `stale_subject:revision`, and her answers to the
current presentations accept both, each naming its settlement. `own-message/admits-nothing`: the feature
proposed under her Telegram-accepted objective is RAW, and no admission, priority or settled effect names
it. `evidence/bound-intake-command`: the acceptances name the intake command that first wrote each
source (equal to intake's own id for that source and content), the Telegram message's id, sender id,
platform date, update and evidence id, and the API request's id, principal and signed digest; evidence
naming another message's intake command, or none, is refused `invalid_input:intake_command` writing
nothing, and the message's own command then accepts. `evidence/same-bound-fields`: both own-message
acceptances and the answered acceptance bind the exact outcome, scope, authority and evidence
requirements, the revision and the bound digest (recomputed here), the owner and the ruling.
`evidence/project-not-his`: olga's Telegram message in proj-c becomes an objective whose acceptor is
zed; her message is refused `not_owner:source` writing nothing. `evidence/repeat`: the same Telegram
message and API request again return the same proposals, a second propose is `already_exists`, and the
acceptance again (one from an earlier read) returns the same acceptance, with the objective and the
journal unchanged and one ACCEPTED history entry. `evidence/stale-revision`: her objective amended to
revision 2; acceptances naming revision 1 or its digest are refused `stale_subject:revision` writing
nothing, and the current one binds revision 2.

Stage environment run (`env -i`, the stage's variables, HOME in `/dev/shm`): 35 passed, 0 failed (26
preamble, 9 rows). The suites of the other readers of the objective service also pass there and in a
normal run: `72_veldo_0077_objectives` (20 rows), `73_veldo_0078_backlog` (20), `72_veldo_0128_reports`
(18), and `68_veldo_0126_intake` (18, normal run).

## Red record

`red-at-0af8dc0.json`: the current suite over `git archive 0af8dc0`, the commit before this change,
unchanged. All 9 rows fail by their own assertion and no region raised: the tree's objective service
has no `accept_message`, so every such command is refused `invalid_input`, the owner's objectives stay
PROPOSED, the refusals are not named `not_owner:source`, `invalid_input:intake_command` or
`stale_subject:revision`, no feature can be proposed under an unaccepted objective, and there are no
acceptance metrics.

## Mutations (finding 150)

Registered in `scripts/check_teeth_mutations.py` with the `own-message-` prefix, each declared falsifier
first; `python3 -B proof/VELDO-0150/drive.py` records `mutations.json` and one applied diff per mutant.
All 11 turn their named rows red by assertion; the baseline and the no-op copy of `control_objective.py`
are green. `check_teeth_mutations.py --finding 150 --jobs 2`: 11 rejected. Finding 77 (the other
mutations of `control_objective.py`) still rejects all 24.

| Mutant | Named rows |
|---|---|
| own-message-non-owner-accepted (AC1 falsifier) | own-message/non-owner-presented |
| own-message-operation-missing | own-message/telegram, own-message/api |
| own-message-path-unobserved | own-message/telegram |
| own-message-acceptance-admits | own-message/admits-nothing |
| own-message-other-intake-command (AC2 falsifier) | evidence/bound-intake-command |
| own-message-sender-unbound | evidence/bound-intake-command |
| own-message-request-digest-unbound | evidence/bound-intake-command |
| own-message-bound-digest-unbound | evidence/same-bound-fields |
| own-message-any-project-owner | evidence/project-not-his |
| own-message-repeat-not-returned | evidence/repeat |
| own-message-stale-revision-accepted | evidence/stale-revision |
