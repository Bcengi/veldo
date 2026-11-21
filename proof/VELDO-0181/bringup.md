# VELDO-0181 brought onto the line, 2026-11-21

Lead decision on the bring-up's part 1 blocker: with VELDO-0231 on the line, VELDO-0177 and the tickets
that waited on it come over in dependency order. Source branch: `agent/claude/veldo-0181`, the ticket's own commits
8fb17e67^..1f416231. On the line it stands on VELDO-0180.
The commits, oldest first, were brought over as one change (their diff ported, not replayed):

- 8fb17e67 VELDO-0181: a conversation's questions are ordinary VELDO-0068 requests the presenter shows and settlement settles once; a turn's authority-s
- 23965448 VELDO-0181: suite 137, the four conversation decisions through the existing flow, the owner alone, and a turn's output carrying no authority
- c78b0906 VELDO-0181: three mutation cases (both spec falsifiers and the publish guard) registered
- d49b0232 VELDO-0181: proof, red at the base, the committed tree without the service diff, the falsifiers applied and restored, the service diff
- 47bf595d VELDO-0181: proof README per AC, the mutation receipts, the suites run and the open items for the lead
- ae8f3a66 VELDO-0181: lead widens the footprint for the service's question path, suite 130 and the unclear route question
- ce1b9bdd VELDO-0181: the service opens the two conversation questions as VELDO-0068 requests and reads the settled choice (OPEN item 1)
- d23eb058 VELDO-0181: suite 130 answers a conversation question through settlement (presenter over a loopback Bot API, Settlement.api_answer) (OPEN ite
- ac3df2d0 VELDO-0181: the unclear route question is a VELDO-0068 request presented on his chat, settled once, its settled choice routing the message; s
- cb7bc0b1 VELDO-0181: suites 68 (0126), 69 (0133) and 93 ask and answer the unclear route question through its decision request
- e98b9564 VELDO-0181: fix round 1 proof: red before and green after for the unclear route rows, the suites rerun, the four mutation receipts, README an
- 29d34737 VELDO-0181: lead widens the footprint to suite 68_veldo_0136_hints and commits its update to the decision request (7/7)
- 14e20cb3 VELDO-0181: his reply to the unclear route question's presentation that is exactly one choice's short form (a bare project name, new project,
- ade18d20 VELDO-0181: mutation case bare181-short-form-dropped (a bare short form never answers the unclear route question)
- c9d21c56 VELDO-0181: fix round 2 mutation receipts, the five 0181 cases each alone
- df5825fd VELDO-0181: fix round 2 proof: suites rerun each alone, README round 2 and OPEN.md item 10 resolved
- b81cea8b VELDO-0181: independent review 2026-11-04, SOUND
- d32d39c9 VELDO-0181: suite 137 rows AC1/unclear-ticket-key and AC1/unclear-free-text: a reply to the unclear route question matching no option still s
- ed06f588 VELDO-0181: his reply to the unclear route question's presentation matching no option still settles it once: a ticket key whose prefix decide
- eb43816c VELDO-0181: mutation case free181-clarification-dropped (a free-text reply never clarifies the unclear route question)
- b67b8472 VELDO-0181: suite 137 AC1/unclear-ticket-key compares its routing with the full form's (equal to the bare name's by AC1/unclear-bare-project)
- 91b48584 VELDO-0181: fix round 3 README Round 3 and OPEN.md side observation 2 resolved
- 1f416231 VELDO-0181: fix round 3 proof: suites rerun each alone, red-before receipt, the six 0181 mutation cases each alone

## What changed in the port

- `.veldo/control_intake.py`: `Intake` takes `request_sign` beside `batches` and `conversations`.
- `scripts/check_teeth_mutations.py`: this ticket removes `Intake._ask` (the unclear question is a decision request the presenter shows) and left two mutants anchored on it. `question-not-sent` (finding 126) anchors on `_present_question`. `hint-lead-double-escaped` (finding 168) moves its double render to the presenter's rendering of a request's brief, where the question is now sent. A reviewer should confirm both.
- Suite 86_veldo_0168_text is red after this ticket and green again after VELDO-0187's batch fix 1 (as on the source branch: `proof/VELDO-0187/batch-fix1.md`).
- `scripts/suites/manifest.json` keeps the line's entries and adds this ticket's; `scripts/suites/requires.json` and `specs/index.md` are written by their generators.
- After the port every registered mutant anchors once in its module, the template sync, docs and personal-setup checks pass, and `validate.py all` exits 0.

## Results on the new base

`bringup-2026-11-21/suites.txt`, each suite alone at this ticket's commit of the port:

| Suite | Result |
| --- | --- |
| 137_veldo_0181_conversation_decisions | 19 passed |
| 68_veldo_0126_intake | 18 passed |
| 68_veldo_0136_hints | 7 passed |
| 69_veldo_0133_dispositions | 33 passed |
| 93_veldo_0152_intake_routes | 24 passed |

Falsifiers (`bringup-2026-11-21/falsifiers.txt`): 6 of 6 registered cases of finding 181 are red on their named row when applied to the module at the head of the chain, each module restored.

The re-anchored cases of other findings named above, run the same way: 2 of 2 red on their named row.

`README.md`, `OPEN.md`, the `suites*.txt`, `falsifiers.txt` and `mutation-*.txt` files beside this one are the source
branch's runs and name its commits. The source branch's review is of that branch; the port has had no review.
