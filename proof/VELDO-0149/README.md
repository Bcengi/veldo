# VELDO-0149 proof: a project activates on any repository this domain adopted, by the owner's signed command or his settled answer

## The design as built

**Where a project may run.** `control_project.Projects._adopted` is the one adopted-repository check: the
execution repository is the repository the service's store is enrolled for (its coordinates, which is
what VELDO-0076 accepted) or one the store binds for this domain (`control_store.bind_repositories`, the
record an adoption writes; `bound_repository(conn, domain, repository)`). Signed activation asks it
before committing and the activating transaction asks it again on the transaction's own connection. A
repository no binding of this domain records, including one bound only in another domain, refuses
`invalid_input:execution_repository` (the name VELDO-0076's `other-repository` case already pins) and
nothing is written. Every activation's observation names its `path` (`signed_command` or
`settled_answer`), its `execution_repository` and its `adoption` (domain, repository, bound path, and
whether the coordinates or a store binding adopted it); `metrics()['activations']` counts accepted and
refused activations by path, and each refusal by name.

**The settled answer.** `Projects(..., settlement=<VELDO-0068 Settlement on the same connection and
coordinates>)` and `activate_settled(request)`. An activation request is an inbox request whose settlement
terms name the `decision_disposition` touchpoint and a target of kind `project_activation`
(`activation_target(proposal)`: the project's id and the digest of the proposal); the proposal is
`activation_proposal(name, fields)`, the signed command's five fields plus the project name. It applies
only when the request is SATISFIED by the settlement of its current version and that settlement's typed
effect is the approval of exactly these terms carrying this proposal. Named refusals, each with nothing
written: `missing_field:<field>` (the same helper, `_bound_fields`, the signed command uses),
`unsettled:no_answer`, `unsettled:not_settled` (answered at the current presentation, not yet settled),
`unsettled:request_closed`, `stale_answer` (the only answers name a presentation or request version that
has since changed), `not_approved:<ruling>`, `invalid_input:settlement`, `stale_subject:brief` when the
request's brief (the text the owner is shown on Telegram) is not exactly `activation_brief(proposal)`, the
plain-text rendering of the project and every bound value (owner, execution repository, charter,
authority policy, coordination budget), as `control_backlog._settled` does for its briefs, and
`not_owner` when the settlement's only principal is not the owner the activation binds. Then the owner must be current and
every activation predicate applies; the commit pins the request, its terms, the settlement, its effect
and the owner's membership, under the command id `project-activation:<settlement id>`. The record is the
signed command's (same fields, digest, state and history edge) with `provenance.source =
settled_answer` naming the request, settlement, receipt, effect and presentation; a second application
refuses `already_exists`.

Not changed: VELDO-0076's criteria and text, the settlement service, the store, the Gate.

## Suite

`scripts/suites/77_veldo_0149_adopted_activation.py`
(`python3 scripts/selftest.py --suite 77_veldo_0149_adopted_activation`). Real SQLite store, OpenSSH
command, journal, enrollment, possession, edge and API signatures; members enrolled by the steward's
signed commands; eight real Git clones enrolled through `control_enrollment.enroll` and resolved by
`resolve_store`, seven bound with `bind_repositories` (six in this domain, one in another); activation
requests recorded as VELDO-0068 terms, opened in the inbox, framed and presented over a loopback Bot API,
answered by the API edge or by a Telegram reply the Acquirer attributes and the protected signer process
signs, and settled by the VELDO-0068 service. Each row is reported once.

| Criterion | Rows |
|---|---|
| AC1 | `adopted/two-repositories`, `adopted/unadopted-refused` (declared falsifier), `adopted/observed` |
| AC2 | `answer/activates`, `answer/binds-every-field`, `answer/unsettled`, `answer/owner-only` (declared falsifier), `answer/stale`, `answer/brief-binds-proposal`, `answer/owner-sees-every-value`, `answer/observed` |

`adopted/two-repositories`: two clones resolve through their signed bindings to this store and are bound
for this domain; the owner's signed activation on each creates one ACTIVE project bound to it.
`adopted/unadopted-refused`: an enrolled clone the store never bound, a clone bound only in another
domain and a repository never enrolled each refuse by name with nothing written, and the same activation
on a bound repository is accepted. `adopted/observed`: the path, repository and binding of the accepted
and refused activations, the counts by path and refusal, no charter text or signature.
`answer/activates`: the owner's API answer settles an activation request for a store-bound repository;
one ACTIVE project results whose record equals the signed command's, with the settlement as provenance;
applying it again refuses `already_exists`. `answer/binds-every-field`: five settled requests, each
omitting one field, refuse `missing_field:<field>`. `answer/unsettled`: unanswered (`unsettled:no_answer`),
answered by Telegram but not settled (`unsettled:not_settled`, and once settled it activates), and a
settled rejection, which activates nothing (its own part) and refuses `not_approved:reject`. `answer/owner-only`: a settlement answered by another current
owner-role member, and an owner's answer for a project another member would own, refuse `not_owner`.
`answer/stale`: the owner's Telegram reply to the first presentation, then the request revised and
presented again (a new deadline); nothing settles and activation refuses `stale_answer`.
`answer/brief-binds-proposal`: the review's case. The requester's brief says "repository-beta with a
small budget" and the proposal names repository-alpha with capacity 999; the owner's Telegram text shows
neither the proposal's repository nor its budget, his accept settles it, and activation refuses
`stale_subject:brief` with no project and nothing written. `answer/owner-sees-every-value`: an activation
request whose brief is `activation_brief`; the owner's Telegram message text, read back from the
loopback platform, shows the project, owner, execution repository, charter purpose and exclusion, every
policy touchpoint beside its role and every budget unit beside its cap (distinctive values, matched
without the rendering's format), and his accept of those bytes activates exactly those values.
`answer/observed`: request,
settlement, receipt, presentation, repository and binding on the accepted observation; the six error
classes distinct; counts by path and refusal; no rationale, charter text or signature.

Stage environment run (`env -i`, the stage's variables): 39 passed, 0 failed (26 preamble, 11 rows and 2
`ran/` rows), about 2 seconds; suite 71 (VELDO-0076) under the same environment: 53 passed. Suites of the touched module, all green: 71 (VELDO-0076), 72 (VELDO-0077),
73 (VELDO-0078, VELDO-0089), 75 (VELDO-0150), 76 (VELDO-0079).

## Red record

`red-at-a166d14.json`: the current suite over `git archive a166d14`, unchanged. All 11 behavior rows fail
by their own assertion (no row raised): the pre-change service accepts only the store's own repository,
so both bound repositories and the control are refused, its observations carry no path or binding, and
it has no settled path (the suite answers it `no_settled_activation`), and its requests carry the
requester's brief, so the owner's Telegram text shows none of the bound values.

## Mutations (finding 149)

Registered in `scripts/check_teeth_mutations.py`, each declared falsifier first; `drive.py` records
`mutations.json` and one applied diff per mutant. All 13 turn their named row red by assertion; the
baseline and the no-op copy are green. `check_teeth_mutations.py --finding 149 --jobs 2`: 13 rejected.

| Mutant | Named row |
|---|---|
| adoption-unchecked (AC1 falsifier) | adopted/unadopted-refused |
| adoption-any-domain | adopted/unadopted-refused |
| adoption-own-repository-only | adopted/two-repositories |
| adoption-unobserved | adopted/observed |
| activation-path-uncounted | adopted/observed |
| settled-answer-any-member (AC2 falsifier) | answer/owner-only |
| settled-field-unbound | answer/binds-every-field |
| settled-unsettled-applies | answer/unsettled |
| settled-rejection-applies (neither ruling nor approval effect required: the rejection activates) | answer/unsettled |
| stale-answer-unnamed | answer/stale |
| settled-provenance-unrecorded | answer/activates |
| settled-brief-unchecked (the review's case) | answer/brief-binds-proposal |
| activation-brief-omits-repository | answer/owner-sees-every-value |

Finding 76 mutates the same module: its `omitted-policy-activates` and `second-activation-replaces`
anchors now name the shared `_bound_fields` helper and the activating branch that calls it (the same
defects, relocated); `--finding 76`: 23 rejected.

`settled-unsettled-applies` still stops at a later check under another name (`not_approved:None`): an
unsettled request has no settlement or effect record, so no mutant can make it activate without
fabricating one. `settled-rejection-applies` now makes the rejection activate, so its row proves the
check stops activation and not only the refusal's name.
