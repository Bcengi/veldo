# VELDO-0075 proof

Andon delivery and authorized resumption through enrolled channels. Specification status, risk and
`.veldo/policy.yaml` are unchanged. This proof is for independent review; it is not a self-approval,
and the canonical gate is run by the lead.

## What was built

- `.veldo/control_andon.py` (engine copy identical, in `init_scaffold._FILES`, not substrate). The
  andon service on the activated ingress's one store connection. It owns three entity kinds, written
  only by its registered `andon_transition` command: `andon_stop`, `andon_notice` and
  `andon_station_contract`.
- **Raising.** `raise_stop` takes one signed command. The signer must be an active member of a type
  the proposal boundary admits (a person, a service or an agent run) whose scope covers the
  repository, with its signature verified against its active key. No role is asked of the requester.
  The stop records the reason, the station, the interrupted unit state and the resolving authority
  (the designated person and the roles an answer requires). In the same transaction the unit moves to
  `AWAITING_AUTHORITY` along its declared edge, carrying the interruption. The enabled stop points are
  build (DISPATCHING, RUNNING, VERIFYING), review (REVIEWING) and coordination (CLAIMED, READY_TO_LAND,
  LANDING). A stop is unknown-effect when the requester says so or when a dispatch of the unit is in
  the `unknown` state. The designated authority must be able to settle the stop and be reached now,
  or the raise refuses by name and writes nothing. It must be eligible by the VELDO-0068 settlement
  service's public `Settlement.eligibility(touchpoint, terms, principal, *, requested_by, scopes)`,
  which returns `(requirement, problems)` from the settlement's own `requirement()` (the
  `decision_disposition` policy AND the named roles, so `project_owner` is always among them) and its
  own authority check, the one `settle` applies; the raise refuses by the first problem
  (`role_not_satisfied`, `independence_not_met`, `unsupported_quorum`) naming the person and the
  missing roles. It must have a valid private chat enrollment, refused as `no_enrolled_chat`. And
  while the VELDO-0073 activation record is qualifying or active, the gate sends only to the chat it
  binds, so a designated person who is not that record's owner and whose chat is not that chat is
  refused as `chat_not_enrolled`; a stopped or absent edge is temporary, so the stop is recorded and
  its notice deferred. An inbox item already under the stop's predictable alias that this service did
  not open for the designated person with its own terms is refused as `foreign_request`, at raise with
  nothing written, and on replay, at notice and at resume. The stop records the effective roles, and
  the roles the requester named as `requested_roles`.
- **The request.** The service, an enrolled service principal with its own key, records VELDO-0068
  settlement terms (touchpoint `decision_disposition`, target the stop by id and digest, the stop's
  roles). It then opens the VELDO-0064 request addressed to the designated person, frames it and
  presents it. `revise_stop` (the requester only) adds to the reason: a new request version with the
  same status, framed and presented again.
- **The notice.** `notify` presents the current request version through the VELDO-0065 presenter on
  the VELDO-0073 activated edge and keeps one `andon_notice` per (request, request version,
  presentation id). The notice holds the chat, the platform's message ids, the presentation id,
  version and digest, and the answer path (a reply to that message, with the offered choices). A key
  already kept is suppressed. No tracker link is used. A notice that cannot reach the designated
  authority (an edge the owner stopped, an owner no longer current, a chat not enrolled or no longer
  valid, an enrollment changed since the activation) is refused under that name, classed `missing_authority` as VELDO-0073 classes `edge_stopped`.
- **Resuming.** `resume` moves the unit to READY only on the settlement of the request's current
  version: it must be the assignment's terminal state with its receipt and typed effect, approve the
  stop's own target, and be the designated person's alone on the presentation that is still current.
  That person must still be an active person holding every role the settlement's own requirement
  named and every role the stop recorded. The resumed unit carries a
  fresh `andon_station_contract` naming the station, the attempt, the unit version it was issued at and
  the settlement, receipt and effect that permitted it. An unknown-effect stop is refused as
  `unknown_outcome` whatever was answered, with its dispatch and reservations untouched.

The module was first judged against the criteria and the threat model of "What the reviewer judges"
with no change needed. Review 75 then found that a raise accepted a designated authority who could
not meet the settlement's requirement, and that resume re-checked only the recorded roles; two filed
items followed (notice refusal classes, and no enrolled chat checked at raise). All four are fixed,
each with a row and a mutation that turns it red. The second review (75b) found that a raise took any
valid enrollment as reachable though the activated edge sends only to the chat its activation binds
(a deputy's stop was recorded and never delivered), and that the raise copied only the roles half of
the settlement's check through a private reach into the settlement module; two filed items followed
(`stale_enrollment` reported as `unavailable_service`, and a request squatted under the stop's alias
taken as the stop's own). All four are fixed, each with cases and mutations that turn them red.

## Rows, falsifiers and red record

Suite `scripts/suites/72_veldo_0075_andon.py` (about 3 s). The authority is real: SQLite store, OpenSSH
signatures on every command and journal record, and the actual protected signer process. The
production ingress is built by `control_channel_ingress.open_ingress` from 0600 host configuration
files and qualified and activated by the owner's signed VELDO-0073 commands. Answers go through the
VELDO-0066 acquirer, the VELDO-0068 settlement service and the authenticated API edge. The Bot API is a
loopback stand-in (`scripts/suites/support/v73_authority.py`), and a socket guard refuses and counts
every connection beyond 127.0.0.1, so no row and no mutant reaches Telegram, and no real token file is
read. Execution units and one dispatch record of unknown outcome are laid as store fixtures; every
stop, notice, answer, settlement and resumption goes through the real signed commands.

| Row | Criterion | What it drives | Mutations (declared falsifier first) |
| --- | --- | --- | --- |
| `stop/any-authenticated-requester` | AC1 | A stop at each of the seven enabled stop states, raised by a worker (an agent run with no role) or a service with no role; reason, station, state and predicate kept; the unit stopped along its edge; the request addressed to the owner, not the requester; a station that does not hold the unit and a disabled stop point refused | `raise-requires-resolving-role`, `resolving-recorded-as-requester`, `station-unchecked` |
| `stop/unauthenticated-refused` | AC1 | A command signed with another member's key and one signed by no member: refused, nothing recorded | `raise-signature-unchecked` |
| `stop/designated-authority-deliverable` | AC1, AC3 (reviews 75, 75b) | A technical_authority-only person designated is refused as `role_not_satisfied` naming the person and `project_owner`; a person with no enrolled chat (the steward) is refused as `no_enrolled_chat`; a project_owner deputy with an enrolled chat of their own, which the owner's active edge does not bind, is refused as `chat_not_enrolled`; a person scoped by the plain string `project-a` and one with no independence group are refused as `role_not_satisfied` and `independence_not_met`, the first problem the settlement's own check and its `eligibility` give them; none writes or sends anything; a stop naming only technical_authority records the effective roles with `project_owner` and its terms carry them | `effective-requirement-not-computed-at-raise`, `enrolled-chat-unchecked`, `eligibility-bypassed`, `reachability-as-any-enrollment` |
| `stop/request-alias-squat-refused` | AC1, AC3 (review 75b, filed) | Another member's request opened first under the stop's predictable alias: the raise is refused as `foreign_request`, nothing written or sent; with only the terms name taken, the stop is recorded and its request refused at terms, and the request the squatter then opens under the alias is refused as `foreign_request` at notice and at resume, nothing sent | `squat-accepted` |
| `notice/each-stop-kind` | AC2 | The build, review and coordination stops each sent once to the owner's chat; the stored correlation equals the published presentation and the platform's message ids; the answer path is a reply to that message | `raise-sends-nothing`, `answer-path-unbound` |
| `notice/new-version-same-status` | AC2 | The requester's revision is request version 2 with the same status; a new message shows the update; its notice has its own presentation and message; a repeat is suppressed; another member cannot revise | `notice-keyed-by-status`, `revision-not-presented` |
| `notice/unreachable-authority-classed` | AC2, observability (filed) | A revision's notice to an owner without `project_owner` is `owner_not_current`, after the owner re-enrolls his chat `stale_enrollment`, after the owner stops the edge `edge_stopped`, after the chat enrollment is revoked `invalid_enrollment`, each observed classed `missing_authority`; with the edge stopped a stop naming the deputy is recorded and its notice deferred as `edge_stopped`; `no_enrolled_chat`, `stale_enrollment` and `chat_not_enrolled` keep their names and class | `unreachable-authority-misclassed`, `stale-enrollment-misclassed`, `stopped-edge-refused-at-raise` |
| `resume/acknowledgement-grants-nothing` | AC3 | A stop noticed, published and acknowledged but not answered does not resume, nor does a pass of the service; the owner's settled reject does not resume | `resume-on-notice`, `any-ruling-resumes` |
| `resume/stale-or-wrong-actor` | AC3 | The owner's reply to the superseded version 1 message, an unenrolled sender, and the steward and the worker through the API edge settle nothing and resume nothing; a settlement whose author has since lost a resolving role does not resume; a settler who lost `project_owner`, which the settlement required for a stop naming only technical_authority, does not resume; nor one who lost a role the running settlement policy required beyond the roles the stop recorded | `stale-answer-resumes`, `resolver-roles-unchecked`, `resume-rechecks-recorded-roles-only` |
| `resume/owner-settlement-fresh-contract` | AC3 | The owner's accept of the current version (2 for the revised build stop, 1 for a coordination stop) resumes the unit to READY with a fresh station contract whose permission is that settlement, receipt and effect; a second resume is refused | `contract-at-stale-unit-version`, `first-version-settlement-only` |
| `resume/unknown-effect-stays-stopped` | AC3 | A declared unknown effect and an unknown dispatch both record an unknown-effect stop; the owner's settled accept resumes neither; the dispatch record is untouched | `unknown-effect-resumes`, `unknown-dispatch-ignored` |
| `install/assets` | all | Scaffold registration, engine copy, laid by the installer | `andon-not-scaffolded` |
| `observability/named-refusals` | all | Every refusal named and classed, no reason text or signature observed, counts and pending stops | `refusal-unclassed`, `reason-text-observed` |

Registry: `scripts/check_teeth_mutations.py --finding 75` (28 mutants, all rejected, each reddening its
named row). `python3 -B proof/VELDO-0075/drive.py` regenerates `mutations.json` and the diffs: each
mutant reds its named row by assertion, and the baseline and a no-op copy of each mutated module are
green. `red-at-9fa7e4d.json`: the current suite against the pre-change tree (`git archive`, unchanged),
where the andon module is absent; every row is red by its own assertions, none by an exception.
`red-at-e5c2bc8.json`: the current suite against the tree before the review 75 fix; exactly the three
rows that fix answers are red, by assertion (the techlead and the chatless steward accepted, a settler
who lost a required role resumed, unreachable notices classed `unavailable_service` or
`stale_subject`).
`red-at-3ed40c1.json`: the current suite against the tree before the review 75b fix; exactly the three
rows that fix answers are red, by assertion (the deputy, the plain-string scope and the no-group
person recorded, the squatted alias taken, `stale_enrollment` reported as `unavailable_service`).

## Pending: AC2's real-Telegram leg

The rows use a loopback stand-in. The real-Telegram leg of AC2 is run once by the lead with the owner
through the running factory (VELDO-0138) and recorded; until then the suite prints it as PENDING and
it is never counted as passed.

## Known limits

- The execution units and the unknown dispatch are store fixtures in the shapes `control_claim` and
  `control_dispatch` write; the units' own lifecycle to those states is other specifications' work.
- A stop whose request could not be opened (terms or inbox refused) stays recorded and stopped; opening
  it again, and lost-send or reconnect handling, are Release 2 recovery.
- The effective requirement and the authority check are the running settlement service's own,
  through its public `eligibility`, so the andon keeps no copy of the journey policy or of the check. The
  policy-change case in `resume/stale-or-wrong-actor` changes that running policy between raise and
  settlement in the suite, the only way a settled requirement can exceed the recorded roles.
- A member who records settlement terms under a stop's alias name before the stop is raised leaves
  that stop recorded with no request of its own (refused at terms, as any unopened request is, and
  Release 2 recovery); a request the member then opens under the alias is refused at notice and at
  resume, so it never stands in for the stop's.
- Resume re-checks the settled and recorded roles itself, as before; the settlement already applied
  its whole check when it settled.
