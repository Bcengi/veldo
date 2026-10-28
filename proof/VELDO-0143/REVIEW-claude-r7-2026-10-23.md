VERDICT: HAS DEFECTS (R7-1 medium, R7-2 medium, R7-3 low, R7-4 low, R7-5 low)

# VELDO-0143 round 7: fix review (claude, 2026-10-23)

This review was done in a fresh context, independent of the builder. The worktree is at a7db6774 and the range is
18ee1a2b..a7db6774. I read the round 6 review, the range's diff of control_channel_presentation.py,
control_project_proposal.py, control_telegram_report.py and control_workflow_cycle_pm.py (the `.veldo/` and
`engine/.veldo/` copies are byte for byte the same: `cmp` exits 0 for all four), DECISIONS 28 to 30, the spec's AC1
and History, round7/README.md, the rows that changed in suites 62 and 110, and the mutations that changed in
scripts/check_teeth_mutations.py.

## Summary

1. On the presented path the binding is sound. The identity and the visibility come only from the choice the
   settlement records (`answered`), and the one judge (`settled`) checks the same thing again. A typed correction
   cannot set either field, whatever it says. A pick that does not match an offered choice is refused
   `unmatched_choice` before anything is recorded. A stale or replayed choice is bound to its request version,
   presentation digest and terms proposal, and only the owner's settlement counts. I could not get a presented
   decision to bind a value the owner did not pick. Two paths still bind a visibility he never picked:
   - His own message, with nothing presented, takes the identity's default visibility, which may be public, and
     reads nothing he wrote about visibility (R7-1).
   - An adopted directory is offered both visibilities, but the adoption path never reads the picked one (R7-2).
2. The pick kind extends the channel the way it is built. `ruling_of` is still the one map from choice to ruling.
   Picks go through the same `offered_choice` folding, the same `unmatched_choice` and `unmapped_choice` refusals
   and the same receipt check (`rulings == [ruling_of(c) ...]`). The new `ambiguous_choice` refusal sits in the
   contract's REFUSALS, and suite 62 has the kind's own row. Approve, reject, return_for_elaboration and
   acknowledgement keep their rulings: a pick never matches a fixed word, `ruling_of('approve x')` is None, and an
   acknowledgement request still refuses any pick as unmapped. The new fold check can leave a new-project
   decision `presented` with nothing presented (R7-3).
3. All free-text binding of the identity and the visibility is gone from the settlement and the correction:
   `named`, `bound` and `identity_named` are removed, and the only remaining readers of text are the name check in
   `correction_problems` and the own-message path. The replacement mutations guard the new binding, with one gap:
   no row or mutation guards the judge's new `no_settled_decision:choices` check (R7-4).
4. service/provisions now requires that the provisioner's end alone makes the pass due. Its new part is the same
   on both branches, and I confirmed newproject143-provisioner-end-unseen is killed here.
5. Security first: R7-1 and R7-2 are the only paths I found to a visibility he did not pick. There is no new outside
   call, credential or logging of message text in the range. The spec's AC1 now contradicts the own-message path it
   keeps (R7-5).

## What I ran (exit statuses read directly)

| Run | Result |
| --- | --- |
| suite 110 at a7db6774 through round2/sandbox_run.py (stage and agent stand-ins) | exit 1, 84 passed, red only service/hand-off (AF_UNIX), as the proof says |
| suite 62 at a7db6774 through round2/sandbox_run.py | exit 0, 42 passed, 0 failed |
| suite 110 with newproject143-provisioner-end-unseen applied to `.veldo/control_service.py` | 83 passed, service/provisions red on "a provisioner whose take-on is withheld ... [provisioning, []]": killed |
| suite 110 with `.veldo/control_project_proposal.py` `if data.get('choices') != choices(presented):` made `if False:` | 84 passed, red only service/hand-off: survives (R7-4) |
| suite 110 with `accept` always offered (`['accept'] if shown else []` made `['accept']`) | proposal/fields and proposal/choices red: killed |
| suite 110 with the judge's `if proposal != expected:` made `if False:` | proposal/choices red: killed |
| `.veldo/validate.py all`; scripts/check_template_sync.sh, check_lint.sh, check_generated.sh | each exit 0 |
| pure-function probes of `nothing_asked`, `choices`, `offered_choice`, `ruling_of`, `pick_of`, and `GI.validate` (scratch scripts outside the worktree, run with `python3 -I`) | as below |

Note on method: suite 110 loads the repository's `.veldo/` copy, not `engine/.veldo/`. My first three mutated runs
edited `engine/.veldo/` and were therefore no-ops. I discarded them and reran against `.veldo/`. The table shows only
the `.veldo/` runs.

## 1. Trying to get a repository created under a value he did not pick

| Attempt | Result |
| --- | --- |
| PM document sets another identity or visibility on a correction | `correction_problems` refuses `invalid_input:correction:identity` or `:visibility` before `build`. The judge refuses again (rows correction-bound and correction-negated). Holds. |
| PM document names an identity or visibility on the first proposal | Only changes what is shown. `accept` approves what is shown, and every other pair is offered as a pick. Holds, by design (DECISIONS 28). |
| Typed correction "use personal", "Personally I'd make it private", "not this account", Cyrillic e "bcengi" | No text is read for either field. Those values stay as shown, or the decision fails by name. Holds. |
| Typed pick that is not offered: Cyrillic e, partial pick ("accept bcengi"), reordered pick ("accept public bcengi"), the pair `accept` already approves | `offered_choice` returns None, so `unmatched_choice`. A fullwidth b "bcengi" folds by NFKC to the real offered pick, which is right: it names exactly that offered choice. Holds. |
| Stale or replayed choice from an earlier proposal | The answer is bound to the receipt of the replied-to presentation (request version, presentation digest), the terms bind `digest(proposal)`, and `settled` requires `terms.proposal == presented` and `answered(presented, choice)`. Holds. |
| A choice picked by someone other than the owner | Unchanged channel attribution: an automated sender is refused `not_owner`, the principal is the receipt's owner, and `settled` requires `principals == [owner]`. Holds. |
| One configured identity | With the identity shown: `accept`, `accept personal public`, return, reject. With none shown: `accept personal private`, `accept personal public`, return, reject. Both visibilities are always a choice and nothing binds silently on the presented path, which matches AC1 ("every configured identity and both visibilities"). Holds. |
| His own message, with an identity whose `default_visibility` is public | Created public with nothing asked (R7-1). |
| An adopted directory, picking a visibility | The pick is recorded and shown, but nothing applies it (R7-2). |

### R7-1 (medium): his own message settles a public repository he never picked

`engine/.veldo/control_project_proposal.py:626` (with `:376`). On the own-message path, `nothing_asked` accepts any
visibility equal to the identity's `default_visibility`, and `offered_entry` fills a null PM visibility from that
default. Nothing reads what his message says about visibility, and `control_git_identity.validate` allows
`default_visibility: public`.

Scenario, run against the function: identity bcengi with `default_visibility` public, PM document identity bcengi,
visibility null. `nothing_asked` returns `[]` for each of these messages:

- "start a new bcengi project called shoal" (he said nothing about visibility)
- "start a new bcengi project called shoal, keep it private"
- "start shoal under bcengi, hidden please"

The decision then settles `own_message`, and `control_effect_executor_creation.py:192` creates the remote public.
In the first case a public repository exists although he picked nothing and AC2 says "private unless he said
otherwise". In the second and third, a PM document that omits the visibility (a PM error, or an instruction carried
inside his message) decides public against his words. That is the PM's document setting the visibility, which the
owner's decision forbids. Suite 110 never sees this because every fixture identity defaults to private
(suite line 239).

Fix: settle unasked only at private. Add a reason, for example `visibility_not_private`, whenever
`visibility_of(proposal) != 'private'`. A public repository then always comes from a pick. Optionally also present
when the message holds a visibility word. Add a fixture identity with a public default and an own-message-doubt
case for it, with a mutation that removes the new reason.

### R7-2 (medium): an adopted directory offers both visibilities, and the pick binds nothing

`engine/.veldo/control_project_proposal.py:277` (picks) and `:746` (repository_decision). `picks` offers both
visibilities for every offered entry, whatever its mode. For `mode == 'adopt'`, `repository_decision` passes only
`p['adoption']` on, and no module on the adoption path reads `remote.visibility`. Of the modules that mention
visibility, only control_repository_creation and control_effect_executor_creation apply it, and only when creating.

Scenario: `projects-bcengi/shoal` is already a Git repository whose origin is a public GitHub repository. The PM
names bcengi. The brief shows "bcengi: directory ... (adopted as it is ...), remote ... (private, under bcengi)" and
offers `accept bcengi public` beside `accept`. He answers `accept` (or picks private) to keep it private. The
decision records private, the repository is adopted public as it is, and the project's work is pushed to a public
repository. The visibility he picked is shown, recorded and judged, but never true.

Fix: for an adopt entry, offer no visibility pick and show its visibility as the existing remote's ("as it is on
GitHub"). Or read the remote's visibility when the entry is laid, show that, and refuse an adoption whose recorded
visibility differs from the remote's. Add a row in which an adopted entry is offered no visibility it cannot keep.

## 2. The pick kind in control_channel_presentation

The pick kind uses the existing mechanism: `PICK_WORD`, `_PICK` and `pick_of` feed `ruling_of`, which already fed
compose, the receipt check (`control_channel_presentation.py:457`), canonical_answer, the answer check,
control_request_settlement (`:509`, `:571`) and control_channel_attribution (`:594`). Matching is whole-choice
after `_fold`, so a part of a pick never matches. Probes:

- "ACCEPT  bcengi   public", "accept-bcengi-public", "accept_bcengi_public" and non-breaking hyphens all fold
  to the offered pick.
- "accept bcengi", "accept public bcengi" and a Cyrillic letter inside a value fold to nothing.

`ruling_of('accept x\n')`, `ruling_of('accept  x')` and `ruling_of('acceptx')` are None. Suite 62 answer/pick-choices
covers the ruling, the presentation, a folded answer, three unmatched answers and the ambiguous refusal, and both
suite-62 mutations target it. The consumer suites in the proof are unchanged between 18ee1a2b and 8ff58403 where
they run here.

### R7-3 (low): identities that fold alike leave every new-project decision presented to no one

`engine/.veldo/control_channel_presentation.py:870` and `engine/.veldo/control_project_proposal.py:938`.
`GI.validate` accepts ids that differ only in case or separator: `work` and `Work`, or `my-org` and `my_org` (both
probed). Their picks fold alike, so compose refuses `ambiguous_choice`. `NewProjects._present` ignores what
`presenter.present` returns, so the decision is written `presented` with nothing presented. The owner is never
asked and never told, and every pass refuses again in silence. This fails closed, so nothing is created, but the
owner learns nothing.

Fix: refuse such a configuration in `GI.validate` (ids must differ after `_fold`). Or have `_present` check the
presenter's outcome and fail the decision by name (`invalid_input:ambiguous_choice`), so his report tells him.

## 3. Free-text binding removed, mutations replaced

`grep` finds no reader of the rationale for the identity or the visibility. The only readers left are:

- `names` and `negates` in `correction_problems`, for the name;
- `nothing_asked`, for the own-message path.

The comment at `control_project_proposal.py:143` to 145 still says the word edges are "for ... an identity his
approval names". That reading no longer exists; it is a stale comment, not a defect.

The five removed mutations' anchors are gone. Their replacements are identity-from-document and
visibility-from-text (correction), pick-ignored (answered), choices-not-offered, unmatched-choice-accepted and the
four own-message mutations, and they guard the new binding.

### R7-4 (low): the judge's choices check has no row and no mutation

`engine/.veldo/control_project_proposal.py:710`. DECISIONS 28 claims "The judge also requires the request's choices
to be exactly `choices(proposal)` (`no_settled_decision:choices`)". With that line made `if False:`, suite 110 is
84 passed, red only service/hand-off: the mutation survives. Today the check is defence in depth, because
`answered` resolves only picks of `presented`. But it is the check that stops a request offering other choices
from settling, and it is the one judge the provisioner, the signer and the take-on rely on.

Fix: add a part to proposal/choices that settles a request whose recorded choices differ from `choices(presented)`
and requires `no_settled_decision:choices`, plus a finding-143 mutation that removes the check.

## 4. service/provisions

The new part (atoll) unlinks the socket, so the take-on is withheld on both branches. It runs a pass only when
`projects_due` is set, and requires `atoll_waiting == 'provisioning'` and exactly one `ended` event naming
`not_taken_on:authority_unavailable`. A pass can only see the end if the provisioner's end made it due. With the
mutation applied here, the part is red with `[provisioning, []]`. The new part does not depend on the socket, so
on the host it is red just as it is here. The lagoon part keeps its socket-branch disjunction, but the row as a
whole now needs the end alone to make the pass due. Sound.

## 5. Other

### R7-5 (low): AC1 contradicts the own-message path it keeps

`specs/VELDO-0143-repository-from-chat.md:107`. AC1 says: "Only the choice he picks binds the identity and the
visibility; neither his typed words nor the PM's document ever sets them". A few lines later it keeps "The first
message, which named both, is itself that answer and nothing is presented". On that path the identity is the PM
document's identity, which his typed words had to name, and the visibility is the identity's default (R7-1).
DECISIONS 29 explains the exception, but the acceptance text a reviewer judges against states the absolute.

Fix: qualify the AC1 sentence ("on a presented proposal, only the choice he picks binds ...; his own message
settles unasked only as AC1's nothing-asked rule allows, at private"), together with R7-1's fix.

Also seen, not findings:

- `control_telegram_report` sends `PICKED_NEXT` for `invalid_input:correction:mode`. That advice (pick the choice
  that names the identity and visibility) does not fit a refused mode.
- The brief lists each identity's visibility as the PM's or the default, even where a pick would change it. The
  pick names its own visibility, so nothing shown is false on the creation path.
