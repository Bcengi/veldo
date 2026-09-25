---
schema: veldo.spec/v1
id: VELDO-0133
title: Ask what becomes of work whose person assignment is declined, canceled or expired
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W96
plan_revision: 3
depends_on: [VELDO-0064, VELDO-0126]
placement: [contracts, tracker, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_assignment*.py"
  - ".veldo/control_assignment*.py"
  - "packs/*/.veldo/control_assignment*.py"
  - "engine/.veldo/control_channel_projection*.py"
  - ".veldo/control_channel_projection*.py"
  - "packs/*/.veldo/control_channel_projection*.py"
  - "engine/.veldo/control_claim.py"
  - ".veldo/control_claim.py"
  - "packs/*/.veldo/control_claim.py"
  - "engine/.veldo/control_intake*.py"
  - ".veldo/control_intake*.py"
  - "packs/*/.veldo/control_intake*.py"
  - "scripts/suites/*_veldo_0133_*.py"
  - "scripts/suites/60_veldo_0064_inbox.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0133-disposition-of-declined-and-canceled-work.md"
  - "specs/index.md"
  - "proof/VELDO-0133/*"
behavior_bearing: true
observability:
  logs: >
    Record the operation (the decline or cancel that opens a question, ask, answer, dispose),
    domain, repository, the source assignment, the disposition question and the blocked unit,
    the addressee and why that principal was chosen, accepted input versions, the outcome
    applied and any named refusal. Never log the free-text instruction, a brief or a signature.
  metrics: >
    Count accepted and refused disposition operations by outcome (close, backlog, other), and
    expose parked units by reason, including awaiting_disposition and ready_to_dispose, beside
    the reasons VELDO-0064 already counts.
  traces: >
    Join the source assignment, its decline, cancel, expiry or failed admission, the disposition
    question and its projection record, the owner's signed answer, the dispose command, the claim,
    unit and backlog transitions it committed, and the intake proposal it produced, by identity.
  error_taxonomy: >
    Distinguish invalid input, missing authority, not authorized, stale subject, no project
    owner, not answered, unavailable service, missing evidence and unknown outcome; a refused or
    unknown disposition is never reported as applied.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: When the assignment a parked unit waits for ends without admitting the blocked work,
      Veldo asks what becomes of that work: it opens one disposition question in the inbox,
      offering close, backlog and other, addressed to the person who declined or canceled, or to
      the project owner when no person did, and the ordinary Telegram projection sends it to
      that addressee's own enrolled chat. Set and completeness: The set is every parked reason
      of VELDO-0064's PARKED_REASONS that has no Release 1 way back (declined, canceled, expired,
      answer_not_admitted), crossed with the principal type that ended the assignment where one
      did: a decline by the owning person; a cancel by a person requester, by a person project
      owner and by an agent_run or service requester; a stored EXPIRED record; and an answer
      whose admission is refused because its key was revoked from before acceptance. The rows
      are derived from PARKED_REASONS and the proposal_commit boundary, so a reason or principal
      type added later with no row fails the check. Drive real signed commands on the real
      configured store and the projection against the loopback Telegram edge; compare each
      question's addressee, offered outcomes, source assignment and request version, blocked
      unit, and the chat the platform reports, with an addressee who has no enrolled chat
      refused as no_enrolled_chat and never sent elsewhere. Falsifier: Address every disposition
      question to the project owner, including one a person declined or canceled; the addressee
      row must fail.
    falsified_by: >
      Address every disposition question to the project owner, including one a person declined
      or canceled; the addressee row must fail.
  - id: AC2
    text: >
      Claim: A disposition question is answered only by its addressee's own signed answer,
      correlated to the question's current request version, choosing one offered outcome, and
      for other carrying non-empty free text inside the signed command. Set and completeness:
      Drive, for each of the three outcomes, a valid answer, and against each question the
      refused forms: a signature that does not verify, an answer signed by another active member,
      a stale request version, a ruling not offered, other with empty text, other whose text is
      supplied beside the signed command rather than inside it, a key revoked from before the
      answer's acceptance, and a decline or cancel of the disposition question itself. Each
      refused form carries its named refusal and leaves the unit, its backlog item, its claim and
      the intake unchanged; each valid answer is admitted by the same admission check VELDO-0064
      uses for any inbox answer. Falsifier: Accept the free-text instruction from the packet
      beside the signed command; the unsigned-instruction row must fail.
    falsified_by: >
      Accept the free-text instruction from the packet beside the signed command; the
      unsigned-instruction row must fail.
  - id: AC3
    text: >
      Claim: An admitted outcome is applied by one authorized dispose command, through the
      declared lifecycle edges and the claim organ's own transitions, and nothing is inferred
      from the free text. Close cancels the unit and its backlog item with the disposition
      recorded; backlog clears the park so an ordinary claim by an eligible holder succeeds;
      other records the instruction verbatim and submits it to the VELDO-0126 common intake as a
      proposed objective or work item for the project manager, attributed to the answering
      person, and changes no unit, backlog item, claim or priority. Set and completeness: The
      three outcomes of the question's choices, each driven through dispose before the answer
      (refused as not_answered), after it, and a second time (the same result for other, a
      stale_subject refusal for close and backlog), plus an ordinary claim through the claim
      Receiver before and after each disposition. The unit, backlog item and claim states are
      read back from the store and the intake proposal from the intake's own reader. Falsifier:
      Apply the ruling other as backlog, releasing the unit instead of submitting the
      instruction to intake; the other-outcome row must fail.
    falsified_by: >
      Apply the ruling other as backlog, releasing the unit instead of submitting the
      instruction to intake; the other-outcome row must fail.
  - id: AC4
    text: >
      Claim: While its disposition question waits, the blocked unit holds no worker or claim and
      is not claimable, and the inbox reports it as awaiting disposition until the answer
      arrives. Set and completeness: Walk every unit of the AC1 set through question opened,
      answered, disposed and, for other, asked again; at each step read waiting_resources,
      parked_units and metrics and an ordinary claim attempt. Require no held claim and no model
      process at any step, a claim refused as parked until close or backlog is applied, the
      reason awaiting_disposition while the question is pending, ready_to_dispose after the
      answer, routed_to_intake after other, and the unit gone from parked_units after close or
      backlog, with parked_by_reason counting each. Falsifier: Report a unit whose disposition
      question is pending under its original reason (declined, canceled, expired or
      answer_not_admitted); the awaiting-disposition row must fail.
    falsified_by: >
      Report a unit whose disposition question is pending under its original reason (declined,
      canceled, expired or answer_not_admitted); the awaiting-disposition row must fail.
required_evidence: [unit, integration]
rollback: >
  Disable the disposition operations, preserve every accepted question, answer, disposition and
  intake proposal, and leave affected units parked and visible; restoring the previous behavior
  requires an explicit operations decision.
---

## Intent

Work that stops for a person must never be parked forever. When the assignment a unit waits for
is declined, canceled, expires or is answered without admitting, Veldo asks the right person
what to do with that work, and then does exactly what that person said through ordinary
authorized commands.

## Context

W96 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 3. The
[design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated 2026-09-22
scope amendments; R18 names the declined, expired and canceled outcomes of an assignment and
requires that waiting for a person holds no worker process or claim lease.

VELDO-0064 built the assignment inbox and left one question open for the owner (its Notes, and
the "Open question for the owner" section of `proof/VELDO-0064/README.md`): a unit whose
assignment is declined or canceled, or whose answer no longer admits, stays parked with no
Release 1 command that claims it, resumes it or returns it to the backlog. It is listed in
`parked_units` and counted in `parked_by_reason`, but nothing decides what becomes of it.

The owner answered in Telegram 28934: "When somebody (a person) declines and cancels, you need
to aks them what to do with it, either permanently close, back to backlog or sonthing else."

That ruling covers the case where a person ended the assignment. For the cases where no person
did (the agent that raised the request cancels it, or the request expires), the lead recommended
in Telegram 28935 that Veldo ask the project owner the same question, and the owner agreed in
Telegram 28936 ("Agreed", replying to 28935). The answered-without-admitting case is treated
the same way: the answer that no longer admits cannot be trusted to speak for its author, so the
question goes to the project owner.

## Out of scope

Hardening is Release 2 and is not part of this criterion or its evidence: no recovery, no
reminders, no reassignment timers and no escalation when a question goes unanswered. No command
here produces EXPIRED; deadline expiry sweeping stays deferred, and this item only disposes of an
EXPIRED record already in the store. The free-text instruction is never interpreted by this
item; its meaning is the project manager's work after intake. Settlement and quorum
(VELDO-0068), presentation receipts (VELDO-0065) and answer acquisition and attribution
(VELDO-0066) are consumed, not changed. The intake (VELDO-0126) is consumed and gains one public
attested submission (Notes); its adapters and behavior are unchanged.

## What the reviewer judges

- Normal use: an assignment that a parked unit waits for is declined, canceled or expires, or its
  answer stops being admitted. Veldo opens one disposition question (close, backlog, other) in the
  inbox, addressed to the person who declined or canceled, or else to the one project owner resolved
  from the unit's ownership chain, and the ordinary Telegram projection sends it to that person's own
  enrolled chat. The addressee answers with their own signed answer; a separate dispose command
  applies it: close cancels the unit (and its backlog item unless sibling work is open), backlog
  clears the park so an ordinary claim succeeds, and other submits the signed instruction verbatim
  through the VELDO-0126 intake's public attested submission, which authenticates the evidence of
  where the answer arrived and requires it to be the answering person's own. While the question waits the unit holds no
  claim or worker and reads awaiting_disposition.
- Threat model: a question addressed to the wrong person (the owner when a person declined or
  canceled, or a guessed owner when none resolves); an answer that is unsigned, signed by another
  member, for a stale request version, choosing an unoffered ruling, with empty other text or text
  outside the signed command, or signed by a revoked key; a decline or cancel of the disposition
  question itself; dispose before the answer, applied twice, or inferring anything from the free
  text; close canceling sibling work; a unit claimable or holding a claim while its question waits;
  an other answer whose arrival is not the answering person's own (another person's API request or
  request id, a message in another person's chat or in a group), which must not squat that source,
  be recorded as that chat, or have the intake's follow-up question sent there.
  The owner's account, the store and the Telegram edge are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); restart and
  recovery (Release 2); forged rows in our own store and files planted in the installed directory; a
  person with no enrolled chat (refused as no_enrolled_chat, never sent elsewhere, by design).

## Notes

The disposition question is an ordinary person assignment in the same inbox, of a new kind whose
choices are exactly `close`, `backlog` and `other`. It names the source assignment, its request
version and the blocked unit, so the existing index, brief, projection and admission apply to it
unchanged and it gets no second record or channel. The unit stays parked on the source
assignment; the claim organ is touched only to clear the park for `backlog`.

Who is asked. A decline is always by the owning person, who is asked. A cancel is by the
requester or a project owner: when that principal is a person, that person is asked; when it is
an `agent_run` or `service`, the project owner is asked. An EXPIRED record and an answer that no
longer admits go to the project owner. The project owner is resolved from the unit's own
ownership chain (unit, backlog item, objective, project) to exactly one active person member
holding `project_owner` whose scope covers the assignment's scope. When that does not resolve to
exactly one person the question is not opened, the refusal is `no_project_owner`, and the unit
stays visible under its original reason; ownership is never guessed.

When the question opens. For a decline or a cancel of an assignment that blocks a parked unit,
in the same store transaction as the decline or cancel, so there is no moment when the unit is
parked with no question. For an EXPIRED record or an answer that no longer admits there is no
Release 1 event to hang it on, so an `ask` command opens it: signed by an active member of the
`proposal_commit` boundary covering the scope, accepted only for a parked unit in one of those
reasons, or in `routed_to_intake`, with no question already open. That last case lets the owner,
or the project manager once it has worked out what the instruction means, ask again. An
assignment that blocks no unit opens no question.

A disposition question can only be answered. Declining or canceling it is refused, because
either would open another question about the same unit; `other` is how a person says "not me" or
"give it to someone else".

Applying the answer. `dispose` mirrors VELDO-0064's `resume`: it is a separate signed command, it
is accepted only while the question admits by the same admission check, and one store
transaction binds the versions of everything admission read. It is signed by an active member of
the `proposal_commit` boundary covering the scope; the decision is the answer's, never the
disposer's. `close` walks the declared `disposition_recorded` edges: the unit to CANCELED and its
backlog item to CANCELED, each carrying the question, the ruling, the answering principal and
the answer's command identity. When the backlog item owns another unit that is not terminal, the
backlog item is left as it is and the recorded disposition says so, so closing one unit never
cancels sibling work. `backlog` clears the park through a new claim organ transition that leaves
the claim released with no holder and no `parked_on`, so the unit is claimable by the ordinary
claim path with its existing eligibility, capability and activation checks, and its backlog item
(already PRIORITIZED or ACTIVE) is unchanged. `other` records the instruction exactly as signed
and submits it through the VELDO-0126 intake's public attested submission, with the answering
person as the principal, the project context from the unit, and the question identity and answer
command identity beside the source, so repeating `dispose` returns the same proposal; the unit stays
parked as `routed_to_intake`, naming the proposal.

Intake source. The answer reaches Veldo through the Telegram edge or through the authenticated
API (the UI's message box uses the API), which are exactly the two source kinds VELDO-0126 admits.
The signed `other` answer carries the evidence of where it arrived, never a bare identity: the id
of the kept VELDO-0066 Telegram evidence of the message, or the request packet the API edge signed.
VELDO-0126 gains one public operation, `Intake.submit_attested(source_kind, evidence, *, principal,
text, project, provenance)`, and `dispose` for `other` calls only it. For `telegram_message` the
intake runs its own Telegram attribution over the kept evidence and requires the sender to resolve
to the answering person in that person's own private chat; for `api_request` it runs its own API
verification (the configured edge's active key) and requires the request's principal to be the
answering person. Only then does it call its common service with the signed instruction as the
text, the unit's project, the source identity and provenance taken from the evidence itself, and
the question and answer command identities beside them. Anything else (missing evidence, a sender
or request principal who is not the answering person, a message outside that person's own private
chat, a packet the edge did not sign, another source kind) is refused by name with nothing written,
and `dispose` refuses it as `not_authorized`, `missing_evidence` or `invalid_input`. No third source
kind exists; the intake's adapters and behavior are unchanged (the lead, 2026-09-24, reversing the
earlier decision that this item does not change VELDO-0126).

Implement canonical engine assets with synchronized installed copies. Derive executable check
registrations from each criterion's declared set; retain the actual observations and each driven
negative-control diff and failing row, registered as finding 133 of the teeth mutation driver.
Real stores, signatures, the claim organ and the loopback Telegram edge are required where
named; the intake is driven through its own real operation, not a fixture of it.

## History

2026-09-23: new draft for PLAN-0019 revision 3, Release 1 stage 3, answering VELDO-0064's open
question under owner Telegram 28934, with the no-person case recommended in 28935 and agreed in
28936. The simple function is in this release; recovery, reminders and reassignment are Release 2.
2026-09-24: built on build-veldo-0133. The inbox opens the disposition question in the decline or cancel
transaction, `ask` and `dispose` are new inbox commands, `unpark` is a new claim organ transition, and
suite 69_veldo_0133_dispositions carries the rows, with the red record at 3e00de0 and finding 133 in
proof/VELDO-0133/. The footprint gains scripts/suites/60_veldo_0064_inbox.py: its parked-units row
declines a unit parked on the owner's assignment, and under AC1 that decline now asks the owner, so the
row reads that unit as awaiting_disposition instead of declined. Only that expectation changed.

2026-09-24: the owner marked this specification ready on Telegram (29088 asked, 29089 "Ready"), after its build.

2026-09-24: review finding (blocking) at 0b3759f: `other` took its source from the signed answer and
called the intake's private `_submit`, skipping its source authentication, so an answer could squat
another person's API request id, be recorded as a message in another person's chat, and have the
intake's project question sent to that chat. The lead reversed the earlier decision not to change
VELDO-0126: the intake gains the public `submit_attested`, the answer carries kept Telegram evidence
or an edge-signed API request, and the footprint gains the intake modules. Suite rows
squatted-request-refused, foreign-chat-refused and no-foreign-follow-up, red at 0b3759f by
assertion (proof/VELDO-0133/red-at-0b3759f.json), and three finding 133 mutations.
