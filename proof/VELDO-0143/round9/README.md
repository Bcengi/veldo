# VELDO-0143 round 9: the round 8 review's findings

Branch agent/claude/veldo-0143. The round 8 review is `../REVIEW-claude-r8-2026-10-23.md`, added unchanged from
e37f0b95 in a6de9354. The code is b22fe3cd, the rows and mutations e2430418, the spec, DECISIONS 34 to 36 and the
module docstring 4a5247cb, and this evidence the commit that adds it. The scratch commit 0fa32df0 (below) is an
object no branch names. Nothing here is a gate result, a review verdict or an approval.

This sandbox refuses AF_UNIX, has no systemd user manager, and may not write the account's graph stage. So suite
110 runs here through `../round2/sandbox_run.py --stage --agent`, as in rounds 4 to 8, and `scripts/verify.sh`
cannot run here. No timer and no polling was added anywhere.

## Each finding: change, row, mutation

| Finding | Change | Rows | Mutations (finding 143) |
| --- | --- | --- | --- |
| R8-1 (medium): an adoption's two-word pick folds like a creation's pick (bcengi beside bcengi-private) | The shape, not a refusal: an adoption's pick is `accept <identity> adopt` (`ADOPT_WORD`). The presentation module's fold keeps the words and their order, so a folded pick's last word is a visibility for a creation and adopt for an adoption: picks of different shapes never fold alike, and picks of the same shape fold alike only when their ids do, which `validate` and `configure_identities` already refuse. So no check was added in `choices` (it could never fire, and no row could guard it) and no id is refused for ending in a visibility word (bcengi beside bcengi-private is not ambiguous once the shapes differ). The brief says an adopted directory's choice names "the identity and adopt" | proposal/adoption-pick-folds (new): bcengi beside bcengi-private is a configuration; bcengi creating shoal is shown and bcengi-private adopting it is offered `accept bcengi-private adopt`; "accept bcengi private", "accept bcengi-private" and "accept bcengi_private" are refused `unmatched_choice` and it stays presented; `accept` creates it under bcengi, private; with no identity shown (cobble) the request is presented, its choices folding apart. proposal/adoption-visibility answers `accept personal adopt`, refuses `accept personal`, and the brief names the new shape | newproject143-adoption-pick-folds (the two-word pick restored) |
| R8-2 (low): a crash between the cancel and the failed write leaves the decision presented to no one | `_present` writes the decision `failed` (`invalid_input:<refusal>`) before it cancels the request, so no crash leaves a presenting decision over a canceled request; `propose` and `resume` only observe the failure. A crash after the failure and before the cancel leaves the request open but never sent: `resume` cancels the request of a decision failed as not presentable whose request is still pending (`_cancel_unpresented`, the same signed command) | proposal/presentation-interrupted, two new parts with a legacy `Bcengi` beside bcengi: tombolo, the service killed just after the cancel, is failed and canceled before and after the next pass; groyne, killed just before the cancel, is failed with its request open, and the next pass cancels it | newproject143-not-presented-canceled-first (cancel, then fail, as in round 8), -unpresented-left-open |
| R8-3 (low): his own message asking for a public repository in other words settles private, unasked | `nothing_asked` presents his message (`words_not_read`) unless every word of it, apart from the project's name and the identity's id or label, is in `PLAIN_WORDS` (a, an, the, new, start, create, make, set, up, begin, please, project, repo, repository, called, named, name, under, with, using, as, for, my, me, it, identity, account): failing closed. The comment at `_VISIBILITY_WORD` no longer claims a joined word counts; it says the words are read whole and that the allowlist decides | proposal/own-message-doubt: "share it with everyone", "publish it", "make it opensource", "publically" and "everyone can see", each presented with `words_not_read` | newproject143-own-message-unread-words |

Finding 143 has 64 cases: 60, plus four new.

## Results here

- Suite 110 at e2430418 (`110-head.json`) and at 4a5247cb (`110-final.json`, the docstring and spec commit): 92
  passed, red only service/hand-off (AF_UNIX, the host's). 92 is round 8's 90 plus proposal/adoption-pick-folds and
  its ran/ row.
- Suite 110's round-9 rows on the round-8 engine (`110-round8-engine.json`): the tree is e2430418 with
  control_project_proposal.py (both copies) taken from 9a6d94fa, run as the scratch commit 0fa32df0. Red:
  proposal/own-message-doubt, proposal/adoption-visibility, proposal/adoption-pick-folds,
  proposal/presentation-interrupted, and service/hand-off (the host's). Each new and changed row is red there.
- Suite 62 at e2430418 (`62-head.json`): 42 passed, 0 failed.
- Finding 143, `../run_falsifiers.py` in worker mode (`falsifiers-143-round9.json`): the 61 cases that target suite
  110, in four partitions in parallel on a `git archive` of e2430418: 61 killed. Each baseline, before and after, is
  red only on service/hand-off and pm/new-project-run (worker mode stands in for nothing). The two suite-62 cases are
  unchanged from round 8, and suite 62 is unchanged; newproject143-scaffold-not-laid is the host's (suite 66).
- `probes.py` (`probes-round9.jsonl`, `probes-round8-module.jsonl`): over 15664 layouts of two or three ids from a
  pool of lookalikes (bcengi, bcengi-private, bcengi_public, bcengi-adopt, bcengi-private-adopt, x, x.private,
  x-public-private, private, public, adopt, accept) that fold apart, every mode and every shown pair: on the
  round-9 module no two choices fold alike and no typed creation pick binds another identity; on the round-8 module
  204 layouts fold alike (the review's scenario B) and 40 typed picks bind another identity (scenario A, first
  `accept bcengi private` binding bcengi-private). The review's 21 phrasings: all presented on the round-9 module,
  every one settled unasked on the round-8 module bar the seven it already presented; three plain messages still
  settle.
- Round 7's `phrasings.py` on the round-9 module (`phrasings-round9.jsonl`): 90 phrasings, 0 not as claimed.
- Consumer suites (`consumer-suites.json`, `../round2/consumer_suites.py`) on `git archive` trees of 9a6d94fa and
  4a5247cb, one after the other: round 8's 48 suites give the same result on both trees. Of them, 103, 58, 59,
  71_veldo_0130_api, 107, 82_veldo_0141, 85_veldo_0158 and 71_veldo_0138_channel_service do not start here, and 17
  are red on both trees (sandbox limits). Only suite 110 reads control_project_proposal's pick, words or
  presentation directly.
- `.veldo/validate.py all` exits 0. check_lint, check_template_sync and check_generated pass.

## Host runs

1. `python3 scripts/selftest.py --suite 110_veldo_0143_new_project`: every row green, service/hand-off included and
   the new proposal/adoption-pick-folds.
2. `python3 scripts/selftest.py --suite 66_veldo_0047_authority`: every row green, authority/installed-assets
   included.
3. `python3 scripts/selftest.py --suite 62_veldo_0065_presentations`: every row green, answer/pick-choices included.
4. `python3 scripts/selftest.py --suite 103_veldo_0142_git_identities`: every row green (it does not start here).
5. `python3 scripts/check_gate_mutations.py --finding 143`: 64 of 64 killed.
6. `bash scripts/verify.sh`.
