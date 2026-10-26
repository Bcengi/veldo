# VELDO-0143 round 7: the identity and the visibility become choices he picks

Branch agent/claude/veldo-0143. The round 6 review is `../REVIEW-claude-r6-2026-10-23.md`, added unchanged from
a39c5a7b in 3047c93c. The owner's decision is Telegram 36174 (asked) and 36175 ("Ok buttons"), 2026-10-23. The
code is 12006f89, the rows and mutations c5266dd4, the spec, DECISIONS 28 to 30 and `phrasings.py` 8ff58403, and
this evidence the commit that adds it. The scratch commit 8018c567 (below) is an object no branch names. Nothing here is a gate result, a review verdict or an approval.

This sandbox refuses AF_UNIX, has no systemd user manager, and may not write the account's graph stage. So suite
110 runs here through `../round2/sandbox_run.py --stage --agent`, as in rounds 4 to 6, and `scripts/verify.sh`
cannot run here. No timer and no polling was added anywhere.

## The design as built

Rounds 3 to 6 each found typed wording that binds an identity or a visibility he never chose (R6-1 "Personally"
binds personal, R6-2 "not this account" keeps the refused one, R6-3 lookalike characters). Reading free text for
these two settings cannot be made safe, so nothing reads it any more.

- The channel's choices mechanism (VELDO-0065: REQUEST_FIELDS `choices`, CHOICE_RULINGS, `ruling_of`,
  `offered_choice`, the `unmatched_choice` and `unmapped_choice` refusals) gains one choice kind, a pick:
  `accept` followed by the values it picks, each one word (`control_channel_presentation.PICK_WORD`, `pick_of`).
  `ruling_of` maps a pick to approve, as CHOICE_RULINGS maps the fixed words. A reply is matched to a pick as to
  any offered choice: the whole choice, folded for case, width, spaces and hyphens, never by its parts. A request
  whose choices fold alike is not presented (`ambiguous_choice`, a new named refusal). No second mechanism: the
  presentation, the Telegram and API answers, the settlement and the assignment record carry a pick exactly as
  they carry `accept`.
- The proposal (`control_project_proposal.build`) offers every configured identity, each with its directory,
  mode, remote and adoption, and shows the PM's identity when it named one. Its choices (`choices`, `picks`):
  `accept` (approves exactly what is shown; only when an identity is shown), one pick
  `accept <identity> <visibility>` for every other pair of an offered identity and a visibility,
  `return_for_elaboration` and `reject`. One answer is one choice (VELDO-0065), so a choice per field could not
  change both fields in one answer; the per-field sets are offered as their combinations, each naming exactly one
  identity and one visibility (DECISIONS 28). The brief names each identity's directory and remote and says that
  only a choice changes them.
- The settlement binds the identity and the visibility only from the choice he picked (`answered`):
  `accept` the values shown, a pick exactly the pair it names, anything else nothing
  (`invalid_input:answer:choice`). The one judge (`settled`) also requires the request's choices to be exactly
  `choices(proposal)` and the decision's proposal to be exactly the one his choice resolves. His reason is never
  read for either field.
- A correction changes only the project's name and the first objective (`correction_problems`). The name binds
  as before (named as a whole word, no negator anywhere); the objective is the PM's reading. The corrected
  document's identity and visibility must be null or the ones shown, else the decision fails
  `invalid_input:correction:identity` or `:visibility` before anything is built, and the judge refuses it again.
  A proposal that showed no identity cannot be corrected into one. His report says so in plain words, and the
  factory PM's instruction says the same.
- His own message (AC1's nothing-asked path, the one place text still decides an identity) settles unasked only
  where it is plain ASCII, holds no negator, names no other configured identity, and the PM set no visibility
  other than the identity's default; any doubt presents it, so he picks (`nothing_asked`, DECISIONS 29).

Removed from control_project_proposal: `named`, `bound`, `identity_named`, the offered entries' `words`, and the
configured-identities parameter of `correction_problems`. Kept: `_NEGATOR`, `negates`, `names`,
`identities_named`.

## Each item of the brief: change, row, mutation

| Item | Change | Rows | Mutations (finding 143) |
| --- | --- | --- | --- |
| 1. choices offered | the pick kind in control_channel_presentation; `choices`, `picks` and the brief in the proposal | proposal/fields (no identity shown: six picks, rulings approve, no plain accept), proposal/choices (identity shown: accept and five picks; the brief names each identity), suite 62 answer/pick-choices | newproject143-choices-not-offered; -pick-unmapped and -ambiguous-choices-presented (suite 62) |
| 2. binds only from his pick | `answered`, `apply_settled`, `settled` | proposal/one-answer ("accept bcengi private" with the reason "Personally I'd make it public, not bcengi" settles bcengi/private), proposal/choices (a pick binds its pair; accept keeps what is shown whatever the reason says; the judge refuses a decision whose identity is not his pick), provision/answered-and-corrected (the picked public is created public) | newproject143-pick-ignored |
| 2. the PM's document never sets them | `correction_problems`, `correct` | proposal/correction-bound (shoal: another identity; spit: another visibility; sandbar: no identity shown), proposal/correction-negated | newproject143-identity-from-document |
| 2. typed text only the name and objective | as above | proposal/correction (reef-watch renamed, visibility as shown although his words said public), proposal/correction-bound (buoy-b: name and objective settle) | newproject143-correction-name-unbound (kept) |
| 5. typed text naming an identity or visibility changes nothing | as above | proposal/correction-phrasings (90 phrasings of the round 3 to 6 reviews, 16 readings each: exactly the four that keep what was shown settle), proposal/correction-negated (15 end to end, among them "Personally I'd make it private", "not this account", the Cyrillic-e "bcengi", "keep it hidden"), proposal/correction-told | newproject143-visibility-from-text |
| 5. an unmatched choice is refused by name | the channel's existing refusal, now reached by every pick he could mistype | proposal/choices (Cyrillic-e and fullwidth-b "bcengi" picks, an unconfigured identity, the shown pair, "use bcengi", "Personally", accept with no identity shown: each `unmatched_choice`, nothing recorded, still presented, and an offered pick then settles), suite 62 answer/pick-choices (the Telegram path) | newproject143-unmatched-choice-accepted (control_request_settlement) |
| own message | `nothing_asked` | proposal/own-message-doubt (negated, two identities, lookalike, PM visibility, hyphen-joined negator) | newproject143-own-message-visibility, -own-message-negated, -own-message-lookalike, -own-message-two-identities; -negators-narrow and -hyphen-negator-ignored re-targeted here |
| 6. the surviving host mutation | the row only | service/provisions: a second provisioner (atoll) whose take-on is withheld must end with its record waiting and exactly one `ended` event naming not_taken_on:authority_unavailable, on both branches | newproject143-provisioner-end-unseen (unchanged; now killed on the socket branch too) |

Removed mutations and why: newproject143-correction-identity-unbound and -correction-visibility-unbound (their
anchors were the textual binding's `bound` lines, now gone; -identity-from-document and -visibility-from-text take
their places), -kept-while-named and -negation-affirms (`bound` itself is gone), and -bare-yes-corrected (an
approval that named no identity: `accept` is no longer offered without a shown identity, and the channel refuses
it, which -unmatched-choice-accepted tests). Finding 143 has 51 cases: 45, less 5, plus 11.

## Results here

- Suite 110 at c5266dd4 (`110-head.json`; 8ff58403 changes only the spec and the proof): 84 passed, red only
  service/hand-off (AF_UNIX, the host's).
- Suite 110's rows on the round-6 engine (`110-round6-engine.json`): the tree is 8ff58403 with the four changed
  modules (both copies) taken from 3047c93c, run as the scratch commit object 8018c567, which no branch names. 65
  passed. Red: proposal/fields, one-answer, correction, choices, correction-bound, correction-negated,
  correction-phrasings, own-message-doubt, correction-told, provision/answered-and-corrected, and with them
  provision/observed, activation/applied and pm/new-project-run, which read the decisions those rows settle; and
  service/hand-off. Suite 62 there (`62-round6-engine.json`): red only answer/pick-choices.
- Suite 62 at 8ff58403 (`62-head.json`): 42 passed, 0 failed.
- `phrasings.py`: on this module (`phrasings-round7.jsonl`) 90 phrasings, 0 not as claimed; on the round-6 module
  (`phrasings-round6-module.jsonl`) 79 not as claimed, 25 of them settling a value that was not shown (among them
  "Personally I'd make it private", "use BCENGI", "n" + Cyrillic o + "t public", "public lol jk").
- Finding 143, `../run_falsifiers.py` in worker mode on a `git archive` of c5266dd4 (`falsifiers-143-round7.json`):
  all 48 cases that target suite 110 were run and all 48 were killed, newproject143-provisioner-end-unseen among
  them. The baseline before and after is red only on service/hand-off and pm/new-project-run (worker mode stands
  in for nothing). The runner judges only VELDO-0143 rows, so it reports nothing for the two suite-62 cases and
  newproject143-scaffold-not-laid (suite 66, the host's). The two suite-62 cases were run through
  `../round2/sandbox_run.py --replace` on 8ff58403 (`62-pick-unmapped.json`, `62-ambiguous-choices-presented.json`):
  each turns answer/pick-choices red (install/assets is red too, only because the replacement edits one of the two
  copies).
- The host's surviving mutation, here (`110-provisioner-end-unseen.json`): with it, service/provisions is red on
  the new part by itself, "a provisioner whose take-on is withheld ... [provisioning, []]": the withheld record
  waits and no pass names its end. That part does not depend on the socket, so on the host it is red as here.
- Consumer suites (`consumer-suites.json`, `../round2/consumer_suites.py`) on `git archive` trees of 18ee1a2b and
  8ff58403, one after the other: round 6's 38 suites and the six further readers of the presentation module
  (63_veldo_0066_attribution, 65_veldo_0067_edges, 70_veldo_0069_bindings, 70_veldo_0073_activation,
  71_veldo_0138_channel_service, 87_veldo_0170_receiver_trust) give the same result on both trees. Suite 62 differs
  only by its new row (41 passed, then 42). This is evidence only for the suites green here: several are red or
  unjudged on both trees here (sandbox limits), among them 71_veldo_0130_api and 71_veldo_0138_channel_service
  (no table), 83, 92, 93 and 96.
- `.veldo/validate.py all` exits 0. check_lint, check_template_sync and check_generated pass.

## Host runs

1. `python3 scripts/selftest.py --suite 110_veldo_0143_new_project`: every row green, service/hand-off,
   service/provisions (its socket branch, with the withheld second provisioner), provision/signing-no-agent with
   its recording socket, and pm/new-project-run among them.
2. `python3 scripts/selftest.py --suite 66_veldo_0047_authority`: every row green, authority/installed-assets
   included.
3. `python3 scripts/selftest.py --suite 62_veldo_0065_presentations`: every row green, answer/pick-choices included.
4. `python3 scripts/check_gate_mutations.py --finding 143`: 51 of 51 killed, newproject143-provisioner-end-unseen
   on service/provisions' socket branch and newproject143-scaffold-not-laid (suite 66) among them.
5. The consumer suites at this branch's head and at 18ee1a2b (round 6's head): first the ones that read the
   presentation module this round extends (63_veldo_0066_attribution, 65_veldo_0067_edges, 69_veldo_0068_settlement,
   70_veldo_0069_bindings, 70_veldo_0073_activation, 71_veldo_0130_api, 71_veldo_0138_channel_service,
   68_veldo_0136_hints, 86_veldo_0168_text, 87_veldo_0170_receiver_trust), then 83_veldo_0154_factory_loop,
   92_veldo_0088_pm_cycles, 93_veldo_0152_intake_routes and 96_veldo_0204_reservation_policies, then the rest of
   round 6's list.
6. `bash scripts/verify.sh`.
