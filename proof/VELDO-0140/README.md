# VELDO-0140 proof: a standing answer delegation the owner renews, and no silent refusal

## The design as built

**The delegation is standing.** A delegation either pins one request version and one presentation
version (both integers, the VELDO-0067 form) or is standing (both `None`); one of each is refused at
grant (`control_membership.pinned`, `standing`, `_t_grant_delegation`). A standing delegation keeps every
other dimension: purpose (assertion kinds), channel, principal, edge key, scope and expiry. The
membership organ's delegated-use predicate compares versions only for a pinned delegation.
`veldo factory setup` (VELDO-0139) now grants the owner a standing delegation for 90 days.

**The per-version binding moved to the assertion.** The protected signer (`control_signer_answers`)
already bound each answer to its exact published presentation receipt, the request version that receipt
presents and the canonical VELDO-0066 evidence. It now also requires, in the committed state under its
store lock, that the request (the inbox assignment) is still at the version the answer names and that
the presentation it names is the request's current one (the presentation head). A reply to a superseded
version is refused `request-mismatch`, a reply to a replaced presentation `presentation-mismatch`, each
unsigned. `delegation_for` names the one current delegation that is standing or pinned to the answer's
versions.

**Renewal is the owner's own signed command.** `bin/veldo channel delegate` (the dispatcher forwards
`channel` unchanged; `control_channel_activation.delegate_command` builds it) reads the running
service's status and signs, with his enrolled key, a VELDO-0025 `supersede_delegation` of his current
delegation (or a `grant_delegation` when he holds none) naming no versions, for `--days` days (default
90, at most 366). The service's router hands it to the channel (`control_service.Service.apply`), and
`control_service_channel.Channel.delegate` admits it only when the signature verifies with the signer's
active key, the signer is a current person member holding `project_owner`, enrolled on this channel's
chat, is the edge's recorded owner, and delegates his own answers, as a standing delegation to this edge
key of answer kinds only; a second grant beside a current delegation is refused. Then
`control_membership.admit` judges the envelope, signature and policy and commits it. The prior delegation
is marked `superseded_by`, never deleted.

**No silent refusal.** After each woken pass the running service looks at the answers it acquired: for
each owner answer the edge could not sign, it replies once to that message in his chat through the
presenter's gated send (the VELDO-0073 activation gate admits it), saying why: no delegation, an expired
one (with the date and `veldo channel delegate`), a changed request, or the signer's named refusal. When
his standing delegation is within 7 days of expiry (or expired unseen) he is told once per delegation,
in his enrolled chat, to renew it. Each message is recorded before it is sent (the presenter's tell
record), so a later pass or a redelivery never repeats it.

Not changed: `authority_contract.edge_assertion_problems` and `settle` (the contract model, not on the
production answer path) still compare a delegation's versions; a standing delegation handed to them
refuses, which fails closed.

## Suite

`scripts/suites/74_veldo_0140_standing_delegation.py`
(`python3 scripts/selftest.py --suite 74_veldo_0140_standing_delegation`). It runs the setup module's own
`setup` into scratch (`/dev/shm/b140-*`), opens the running service's channel from the installed ingress
configuration, and qualifies and activates it with the owner's own signed commands; every answer goes
through the protected signer process, and every Bot API exchange to the loopback stand-in behind a
socket guard. The installer's worker-profile host qualification and the user manager it asks are
stand-ins, so the real systemd user manager is never read or used. Each row is reported once.

| Criterion | Rows |
|---|---|
| AC1 | `answers/version-1`, `answers/revised-version-2` (declared falsifier), `answers/re-presented`, `refused/by-name` |
| AC2 | `renew/owner-only` (declared falsifier), `renew/route` |
| AC3 | `told/why` (declared falsifier), `told/renew` |

`answers/*`: requests at version 1, revised to version 2, and presented a second time at version 1 each
settle from the owner's reply, each signed under the one delegation setup granted, with no delegation
granted in between. `refused/by-name`: inside the edge's signing of a real answer (its evidence still
undecided), the same answer bound to another channel, actor, scope or edge key is refused by name with
no signature; his replies to the superseded version-1 message and to the replaced presentation are
refused `request-mismatch` and `presentation-mismatch`, unsigned, settle nothing, and he is told once
each. `renew/owner-only`: delegate commands signed by another person member holding `project_owner`
(for himself and for the owner), an agent run, the service principal, with no signature, and a second
grant beside the current delegation are each refused by name and write nothing; the owner's own is
accepted, the prior delegation is kept and marked superseded, and the superseded one signs nothing
(`stale-delegation`). `renew/route`: `bin/veldo channel delegate` reaches the command module;
`delegate_command` builds a standing supersede of his current delegation; `Service.apply` hands it to
the channel, which accepts it. `told/why`: with no delegation (revoked) and after expiry his answer is
unsigned, nothing settles, and one reply in his chat names the reason and `veldo channel delegate`,
sent through the gate; a later pass says nothing more; the expired delegation named directly is
refused `delegation-expired`. `told/renew`: with 3 days left he is told once to renew, through the gate,
and his answer meanwhile still settles.

Stage environment run (`env -i`, the stage's variables): 34 passed, 0 failed (26 preamble, 8 rows), about
10 seconds.

## Red record

`red-at-cda96f5.json`: the current suite over `git archive cda96f5`, unchanged. All 8 rows fail by their
own assertion: setup grants a delegation pinned to version 1, so the revised and re-presented requests do
not settle; the signer signs the replies to the superseded version and presentation; there is no
`delegate` command, route or builder; and the owner is told nothing.

## Mutations (finding 140)

Registered in `scripts/check_teeth_mutations.py` with the `delegation-` prefix, each declared falsifier
first; `drive.py` records `mutations.json` and one applied diff per mutant. All 12 turn their named row
red by assertion; the baseline and the no-op copies (one per mutated module) are green.
`check_teeth_mutations.py --finding 140`: 12 rejected.

| Mutant | Module | Named row |
|---|---|---|
| delegation-setup-pinned-to-version-1 (AC1 falsifier) | control_factory_setup.py | answers/revised-version-2 |
| delegation-signer-pins-versions | control_signer_answers.py | answers/version-1 |
| delegation-membership-pins-versions | control_membership.py | answers/version-1 |
| delegation-request-currency-unchecked | control_signer_answers.py | refused/by-name |
| delegation-presentation-currency-unchecked | control_signer_answers.py | refused/by-name |
| delegation-non-owner-accepted (AC2 falsifier) | control_service_channel.py | renew/owner-only |
| delegation-second-grant-accepted | control_service_channel.py | renew/owner-only |
| delegation-renewal-built-as-grant | control_channel_activation.py | renew/route |
| delegation-route-missing | control_service.py | renew/route |
| delegation-refusal-untold (AC3 falsifier) | control_service_channel.py | told/why |
| delegation-expiry-not-named | control_service_channel.py | told/why |
| delegation-renewal-untold | control_service_channel.py | told/renew |

The other findings with mutations in the modules this changes still reject: 25 (3), 47 (38), 67 (18),
73 (24), 138 (14), 139 (21), and finding 130's four `control_service.py` mutants, each run through the
registry's own materializer and worker.
