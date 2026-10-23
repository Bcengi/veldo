VERDICT: HAS DEFECTS (R8-1 medium, R8-2 low, R8-3 low)

# VELDO-0143 round 8: fix review (claude, 2026-10-23)

This review was done in a fresh context, independent of the builder. The worktree is at 9a6d94fa and the range is
a7db6774..9a6d94fa. I read the round 7 review, the range's diff of control_project_proposal.py,
control_git_identity.py and control_telegram_report.py (the `.veldo/` and `engine/.veldo/` copies are the same:
`cmp` exits 0 for all three), the spec's AC1, AC2 and History, round8/README.md, the changed rows of suite 110 and
the changed cases of scripts/check_teeth_mutations.py.

## Summary

1. R7-1 is fixed for what it was about. His own message now settles unasked only when the proposal's visibility is
   private (`visibility_not_private`), whatever the identity's default or the PM's document says, so a public
   repository never comes from his own message. A message with a word on the list in `_VISIBILITY_WORD` is
   presented. Indirect wording that is not on the list settles at private with nothing asked (R8-3). That is the
   safe direction, but it does not keep AC2's "private unless he said otherwise".
2. R7-2 is fixed as the round 7 review's first option: an adopt entry records `as_on_remote`, is offered as
   `accept <identity>` alone, the brief says "visibility as it is on GitHub", `resolve` refuses a visibility for
   it, `proposal_problems` refuses a resolved adoption recording anything else and a creation recording
   `as_on_remote`, and a correction cannot rename a shown adoption into a creation. The new two-word pick shape
   makes a pick that the owner did not see match what he typed (R8-1).
3. R7-3 is fixed: ids that fold alike are refused in `validate` and when a later id is added, and a request the
   presenter refuses for good fails the decision by name, his report saying why. One crash window between the
   request's cancel and the decision's `failed` leaves the decision presented to no one (R8-2).
4. R7-4 and R7-5 are fixed: proposal/choices has a part requiring `no_settled_decision:choices`, and its mutation is
   killed here. AC1's text now matches the code, apart from what R8-1 breaks.
5. The companion fix in 9a6d94fa changes exactly the two cases it names and nothing else.

## What I ran (exit statuses read directly)

| Run | Result |
| --- | --- |
| suite 110 at 9a6d94fa through round2/sandbox_run.py with its stage and agent stand-ins | runner exit 0; 90 passed, red only service/hand-off (AF_UNIX, the host's), as the proof says |
| suite 62 at 9a6d94fa through round2/sandbox_run.py | runner exit 0; 42 passed, 0 failed |
| seven finding-143 mutations on suite 110 (sandbox_run.py replacing the anchor in `.veldo/`): judge-choices-unchecked, own-message-visibility, own-message-visibility-word, adoption-visibility-offered, adoption-renamed-created, identities-fold-alike, not-presented-left-presented | each killed on exactly its declared rows (plus service/hand-off, red at baseline here) |
| the two suite-62 cases (newproject143-pick-unmapped, -ambiguous-choices-presented) in worker mode, `materialize` then the worker entry point, on a `git archive` of 9a6d94fa | with the companions: worker exit 0, answer/pick-choices red, killed. With the companions removed (the state before 9a6d94fa): worker exit 1, FileNotFoundError on control_channel_presentation_text.py |
| `cases()` at 126f047f against 9a6d94fa | 2673 cases on both; only those two differ, and only in `companions`; finding 143 has 60 |
| `.veldo/validate.py all`; scripts/check_template_sync.sh, check_lint.sh, check_generated.sh | each exit 0 |
| pure-function probes of `says_visibility`, `negates`, `picks`, `choices`, `answered`, `brief`, `proposal_problems`, `offered_choice` and `presentation_fold` (scratch scripts outside the worktree, run with `python3 -I`) | as below |

I could not run check_gate_mutations or verify.sh here (the sandbox's Git common directory is not available to the
coordinator), so the host's 60 of 60 is the builder's result. My sample agrees with it.

## 1. R7-1: his own message

The code (`engine/.veldo/control_project_proposal.py:678` to 681) adds `visibility_not_private` whenever
`visibility_of(proposal) != 'private'`, and `visibility_in_message` whenever `says_visibility(text)`. With an
identity whose default is public, the offered entry is public, so his message is always presented. The presented
proposal shows public and `accept` approves exactly what it shows, which is his tap on a shown value. An adoption is
`as_on_remote`, not private, so his own message never settles an adoption. Rows and mutations guard both reasons.

Probes of `says_visibility`:

| His words | Word found | Outcome when otherwise unasked |
| --- | --- | --- |
| "open source it", "open-source it", "in the open", "visible to all", "make it public-facing", "privately" | yes | presented |
| "nobody else should see it" | no, but `negates` | presented |
| "share it with everyone", "publish it", "make it opensource", "OSS please", "everyone can see it", "on my github profile for all to see", "releasing it to the community", "free software", "publically" | no | settled, created private (R8-3) |
| "keep it to ourselves", "for the team only", "just for me", "keep it confidential", "restricted access" | no | settled, created private, which is what he asked |

No message makes a repository public without a pick. That was R7-1's security point, and it holds.

### R8-3 (low): his own message asking for a public repository by other words is settled private, unasked

`engine/.veldo/control_project_proposal.py:262` (`_VISIBILITY_WORD`) with `:680`.

Scenario: identity bcengi, default private. He writes "start a new bcengi project called shoal and share it with
everyone" (or "... publish it", "... make it opensource"). There is no negator, no listed word, and the identity
and project are each named once, so `nothing_asked` returns `[]`. The decision settles `own_message` and the
remote is created private. He asked for something else and was asked nothing. AC2 says "at the chosen visibility
(private unless he said otherwise)", and round 8's DECISIONS and the brief say his message is presented "when it
holds a word of visibility". This is not a disclosure: the fault is in the safe direction, and he can change
visibility on GitHub. But a finite list of words cannot settle "he said nothing about it", and the comment at
`:259` ("a word joined to another still counts") is not true for "opensource" or "publically".

Fix: settle unasked only when his words hold nothing beyond what the rule has read. For example, present unless
every word of his message, apart from the project's name and the identity's id or label, is on a short allowlist
("start", "new", "project", "called", "named", "a", "under", ...). Or have the own-message settlement's report say
"created private; to make it public, ask again and pick public". Add the phrasings above as own-message-doubt
cases.

## 2. R7-2: an adopted directory

Rendered brief for an adopt entry: `remote https://github.com/quay/shoal (visibility as it is on GitHub, under
quay)`; "Identity: quay, visibility as it is on GitHub. Answer accept to approve exactly that."; choices `accept`,
`accept personal private`, `accept personal public`, return, reject; no visibility is offered for quay.
`proposal_problems` on the answered adoption is `[]`, and with `visibility: private` forced in it is
`invalid_input:proposal:remote`. Nothing downstream reads `remote.visibility` for an adoption:
control_effect_executor_creation.py takes the adoption path at `:165` before `:192` reads it. Sound as designed.

Not a finding: the brief does not say whether the existing remote is public. Nothing on the adoption path reads it
(prepare checks only the origin's owner), so "as it is on GitHub" is the honest wording. Showing the actual
visibility would need a read from GitHub when the entry is laid. That is a design choice for the owner to make.

### R8-1 (medium): an adoption's one-word pick folds like a creation's pick, so a typed answer binds an identity he did not name

`engine/.veldo/control_project_proposal.py:309` (the adopt pick `accept <identity>`), with
`control_channel_presentation.py:283` (`_fold` makes '-' and '_' spaces) and `engine/.veldo/control_git_identity.py:60`.

Before round 8 every pick had three words after folding (`accept <identity> <visibility>`, an id that holds '-'
gives more). Round 8 adds two-word picks for adoptions, so an adopt identity whose id is another identity's id
joined by '-' or '_' to a visibility folds like that identity's creation pick. `validate` compares only ids with
each other, so it accepts `bcengi` beside `bcengi-private` (probed: two folded ids).

Scenario A, run against the functions: identities bcengi and bcengi-private. For project shoal, bcengi creates
(shown, private) and `projects-bcengi-private/shoal` is already a repository (adopt). `choices` is `accept`,
`accept bcengi public`, `accept bcengi-private`, return, reject. These fold apart, so the request is presented. He
wants bcengi private and types the template the brief gives him, "accept bcengi private". `offered_choice` folds
it to `accept bcengi-private`, and `answered` binds identity bcengi-private, mode adopt. The project is adopted
under the other identity's directory, remote and credential. He typed bcengi. The round 7 review's row "the pair
`accept` already approves" (a typed pick of the shown pair is refused `unmatched_choice`) no longer holds in this
configuration.

Scenario B: the same identities with no identity shown. `choices` holds `accept bcengi private` and
`accept bcengi-private`, which fold alike, so compose refuses `ambiguous_choice`, and every new project with that
name fails. His report then says "Give each Git identity an id that differs from the others by more than case, '-'
or '_'", which they already do, and the configuration he has was accepted.

Fix: give an adoption's pick a shape that no creation pick can fold into. For example, keep three words with a
fixed word that is not a visibility and cannot end an id the same way after folding (`accept <identity> as-is`
needs the same care), or check it where it is decided: in `choices`, refuse (or fail the decision by name) when any
offered choice folds like any `accept <id> <visibility>` of an offered identity, including the shown pair. Also
refuse, in `validate` and `configure_identities`, an id that folds like another id followed by " private" or
" public". Add a row with bcengi and bcengi-private (adopt) in which "accept bcengi private" is refused
`unmatched_choice`, and a mutation that removes the check.

## 3. R7-3: ids that fold alike, and a request that cannot be presented

`validate` refuses work/Work, my-org/my_org and a.b/A.B, and `configure_identities` refuses an id added later that
folds like a configured one; both rows and mutations are killed here. `_present` reads the presenter's outcome, and
a NOT_PRESENTABLE refusal cancels the request and raises `NotPresented`. `propose` and `resume` fail the decision
`invalid_input:<refusal>` (`presenting` to `failed` is added to TRANSITIONS), and the report has the reason and
what to do for `ambiguous_choice`. `unmapped_choice` and `presentation_too_long` get the generic "could not be set
up" report with the reason named, which is enough.

`presentation_fold` loads control_channel_presentation.py beside control_git_identity.py by path on every
`validate`. Every suite that loads control_git_identity copies the whole `.veldo/` (103, 110 checked), and the
engine installs as a whole, so this holds. It does cost a module load per call.

### R8-2 (low): a crash between the cancel and the failed write leaves the decision presented to no one

`engine/.veldo/control_project_proposal.py:1000` to 1002 with `:1015` to 1023.

`_present` cancels the request (`inbox.apply(... operation='cancel' ...)`) and only then raises `NotPresented`,
whose handler writes `failed`. If the service stops between the two, the decision is still `presenting`. At the
next pass `resume` calls `_present` again: terms, open and frame replay, and `presenter.present` now meets a request
whose inbox category is `canceled`. `bindings` (`control_channel_presentation.py`, `brief.get('category') !=
'pending'`) refuses `stale_subject`, which is not in NOT_PRESENTABLE. So `_present` returns the request, and
`resume` writes the decision `presented`. Its request is canceled and never settles, `apply_settled` skips it
forever, the name stays in LIVE, and he is never told. That is the state R7-3 removed, and it is reachable in the
crash window that the module's "PRESENTED ONCE, EVEN ACROSS A CRASH" claims to cover.

Fix: write the decision `failed` before canceling the request, or have `_present`/`resume` treat a request whose
inbox category is `canceled` as `NotPresented` with the recorded refusal. Add a part to
proposal/presentation-interrupted that stops after the cancel and requires `failed` after `resume`.

## 4. R7-4 and R7-5

proposal/choices stands in `PP.choices` as `['accept', 'reject']`, settles the request and requires
`no_settled_decision:choices`. With the check made `if False:`, proposal/choices is red here: killed. The proof says
truthfully that the round 7 engine was already green on this row; the row's teeth come from the mutation.

AC1 now says the binding is by pick on a presented proposal, his own message settles only at private, never an
adoption, and an adopted directory is offered by its identity alone. That matches `nothing_asked`, `picks` and
`answered`, except where R8-1 binds an identity he did not pick. Claim and falsifier are unchanged. The report's
`invalid_input:correction:mode` advice no longer tells him to pick an identity and visibility.

## 5. scripts/check_teeth_mutations.py (9a6d94fa)

The five lines give `RENDERER_COMPANIONS` to exactly newproject143-pick-unmapped and
newproject143-ambiguous-choices-presented. They are registered after the loop at `:10360` that gives
renderer-loading cases their companions, so that loop never reached them. `cases()` before and after differs only in
those two cases' `companions`. With the companions the workers run and the cases are killed; without them each
worker fails FileNotFoundError on control_channel_presentation_text.py, as the commit says. It changes only what it
says.

## 6. Other

Security first: R8-1 is the one path I found where the decision binds an identity and mode he did not name. It
needs two configured ids related as `X` and `X-private` (or `_public`), and an adopted directory. No new outside
call, credential handling or logging of message text is in the range. The cancel in `_present` is signed and keyed
by the request's alias, like the other commands there. `as_on_remote` cannot reach control_repository_creation:
`offered_entry` refuses it for a creation, and `proposal_problems` refuses a creation recording it.
