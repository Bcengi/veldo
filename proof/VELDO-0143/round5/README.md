# VELDO-0143 round 5: the round 4 review's findings

Branch agent/claude/veldo-0143. The review is `../REVIEW-agy-r4-2026-10-23.md`, added unchanged from
8b895ed1 (the head of agent/agy/review-0143-r4) in dca6b278. The code is eb690f76, the rows and mutations
b64f5167 (one mutation's target list narrowed after its run, below), the footprint, history and DECISIONS 24
and 25 c6a59f7c. 8fdaa7f5 updates the proof for the owner's move of AC3's first-unit observation to VELDO-0188.
Nothing here is a gate result, a review verdict or an approval.

This sandbox refuses AF_UNIX, has no systemd user manager, and may not write the account's graph stage. So
suite 110 runs here through `../round2/sandbox_run.py --stage --agent`, as in round 4. The full gate
(`scripts/verify.sh`) cannot run here. No timer and no polling was added anywhere.

## Results here

- Suite 110 at dca6b278, before any change (`110-base.json`): 69 passed, red only service/hand-off (AF_UNIX).
- Suite 110 at 8fdaa7f5 (`110-head.json`): 76 passed, red only service/hand-off (AF_UNIX, the host's).
- Suite 110's round-5 rows on the round-4 engine (`110-round4-engine.json`): the tree is 8fdaa7f5 with the six
  changed `.veldo` modules (both copies) taken from dca6b278, run as the scratch commit object 2e8feac2, which no
  branch names. 71 passed. Red: proposal/correction-negated, proposal/correction-phrasings,
  activation/factory-intake-current, activation/factory-paused-resumed, activation/new-projects-kept and
  service/hand-off. Each new row fails without its fix:
  - The final-period, both-ruled-out and ambiguous corrections settle (`('settled', None)`).
  - 23 of the review's phrasings are judged wrongly.
  - After the activation, the factory intake's candidates lack kestrel, and the route to it is refused
    `unauthorized:project`.
  - While the factory project is paused, the kestrel line builds cycles, so the resumed factory line has none.
  - After the failed first build, `new_project_record` is not registered at all.
- `phrasings.py` over the module alone: `phrasings-round5.jsonl` 42 cases, 0 not as expected (10 recorded
  limits, printed and not judged). `phrasings-round4.jsonl` (the dca6b278 module): 23 not as expected.
- Finding 143, `../run_falsifiers.py` in worker mode, on the working commit below (`falsifiers-143-round5.json`).
  14 cases were run: the nine new ones and the five whose anchors moved. 13 were killed. The baseline before and
  after is red only on service/hand-off and pm/new-project-run (worker mode stands in for nothing).
  `newproject143-and-ends-clause` turned proposal/correction-negated red but left proposal/correction-phrasings
  green. That row counts any `invalid_input:correction:` code as a refusal, and with this mutant "don't use
  bcengi and personal" is still refused, but as ambiguous. So its target list is now correction-negated alone
  (d2dc5f36), which tells the two codes apart. Rerun on a `git archive` of d2dc5f36 (`falsifiers-and-ends-clause.json`): killed. So all 14 are killed.
  The other 31 cases of finding 143 have modules and rows that this round does not change. Their anchors are
  each found exactly once. They were not rerun here and are on the host list.
- Consumer suites (`consumer-suites.json`, `../round2/consumer_suites.py`): ad37b673 compared with the working commit below, one
  after the other on `git archive` trees. These are round 4's 36 suites, plus 82_veldo_0141_execution_record and
  85_veldo_0158_credential_delivery, two more Intake callers. All 38 give the same result on both trees: the same
  table count and the same red rows. That is evidence only for the suites green here: among the Intake callers,
  68 (both), 69 (both), 72_veldo_0077, 73_veldo_0078, 75, 76, 82_veldo_0085, 84, 86_veldo_0168 and 91_veldo_0151.
  18 suites are red on both trees here, or stop before their rows (sandbox limits: AF_UNIX, the user manager, the
  graph stage). 93_veldo_0152_intake_routes (11 red), 92_veldo_0088_pm_cycles (20), 83_veldo_0154_factory_loop
  (11) and 96_veldo_0204_reservation_policies (19) are among them, so the R4-3 and R4-5 changes are not judged
  by them here. They are on the host list.
- `.veldo/validate.py all` exits 0. check_lint, check_template_sync and check_generated pass.

The 14-case falsifier run and the consumer suite comparison ran on a `git archive` of a working commit, 5ee4b369,
which no branch names. Its engine and suite are those of b64f5167 with one byte-level difference: the two
regular expressions in control_project_proposal.py (`_NEGATOR`, `_ANSWERED_NO`) held a literal right single
quotation mark instead of the `\u2019` escape. The pattern is the same. That character was replaced before
eb690f76 (ASCII only), and suite 110 at 8fdaa7f5 and the narrowed rerun ran on the committed code.

## Each finding: fix, row, falsifier

| Finding | Fix | Row (red on the round-4 engine) | Registered mutation, here |
| --- | --- | --- | --- |
| R4-1 medium | `_LEFT_EDGE`/`_RIGHT_EDGE`: a '.' or '-' continues a word only when a letter, digit or underscore follows (left: precedes) it. `negated()` fails closed. A shown value counts as negated when any occurrence of its word, matched from a word's start with nothing required after it, has a negator before it in its clause, or "? no" right after it | proposal/correction-negated: "Not under bcengi." with bcengi kept fails `:identity`, and "Keep it private, not public." with public kept fails `:visibility`. "Use personal." and "Keep it private." (shown public) settle as he said. proposal/correction-phrasings: "don't host it publicly", "nothing bcengi-owned" | newproject143-word-edge-period (the round-4 edge): killed. newproject143-kept-value-whole-word: killed |
| R4-2 medium | "neither" is a negator. An "and" whose next word is another value of the field ends no clause, and "or" and "nor" end none. `ambiguous()`: a value affirmed in a clause that began at a bare "and", after a clause negating another value of the field, is refused `invalid_input:correction:<field>:ambiguous` | proposal/correction-negated: "neither personal nor bcengi" and "don't use bcengi and personal" read as personal fail `:identity`. "don't use bcengi and use personal" fails `:identity:ambiguous`. proposal/correction-phrasings: those, plus "dont use bcengi or personal" | newproject143-and-ends-clause: killed (on its narrowed target). newproject143-ambiguity-ignored: killed |
| R4-3 medium | Intake reads its projects when they are judged. `projects` may be a callable, and `Intake.projects` is a property. The factory line's intake (from_line) and the activation's are given `control_intake.store_projects(conn)`, read inside the record and route transitions. The activation's restore is unchanged: it puts back only what was there before, and the intake it puts back now knows the new project | activation/factory-intake-current: after factory-line-kept's two passes, the registry's intake record and route are the factory line's intake. "add a tide table page to kestrel" is recorded `inbox` with kestrel among the candidates and hints. The factory PM's existing_project route to kestrel is accepted, and the request is now kestrel's | newproject143-intake-projects-built (the rows read once, at build): killed |
| R4-4 low | Negators added: cannot, dont, wont, cant, didnt and the other apostrophe-less n't forms, neither, nothing, except, other than, anything but, avoid, and "? no". DECISIONS 24 now lists what remains, each item measured by `phrasings.py` and no claim beyond it | proposal/correction-phrasings: 29 refused and 7 settled phrasings | newproject143-negators-round4 (the round-4 list): killed. newproject143-answered-no-ignored: killed |
| R4-5 low | `Line.build_cycles`: another line builds none while the factory line has no cycles and the store has a factory project, in any state. DECISIONS 25 says why the factory project is part of the condition | activation/factory-paused-resumed: the factory project is paused, and a new service and loop start with the kestrel line visited first. Over two passes no line builds cycles. The factory project is resumed, and its cycles then run on the factory line with its owners on the connection. Its take is accepted, and no other line holds cycles | newproject143-paused-factory-owners-taken (the round-4 condition): killed |
| R4-6 low | `from_line` builds `service.new_projects()` before it takes the registrations, under the same conditions as before | activation/new-projects-kept: a service with no new-project decisions built, on a connection without `new_project_record`. Its factory line's first build fails at Grooming: the presenter is seen on another connection, on that pass only. The next pass builds the cycles, and the operation is registered for the decisions those cycles hold | newproject143-new-projects-in-snapshot: killed |

Re-anchored, each killed here on its own target row: correction-identity-unbound and
correction-visibility-unbound (now the `elif` after the ambiguity check), cycles-owners-after (after the R4-6
block), factory-owners-taken (the new deferral condition) and negation-ignored (`_occurrences`). Finding 143 has
45 cases in all.

## Owner's decision since round 4

AC3's first-unit observation moved to VELDO-0188 AC1 (Telegram 36153, approved by 36156). See 5e934808 and
ad37b673. `../round4/README.md`, `../README.md` and `../manifest.json` now say so, and they name the seed
`../round4/first-unit-for-0188.py`. specs/VELDO-0188-a-line-for-every-project-at-run-time.md is in VELDO-0143's
footprint because that decision moved AC3's sentence into its AC1. scripts/gate_unconfined.json is not touched.

## Host runs

1. `python3 scripts/selftest.py --suite 110_veldo_0143_new_project`: every row green, with service/hand-off,
   provision/signing-no-agent with its recording socket and pm/new-project-run among them.
2. `python3 scripts/selftest.py --suite 66_veldo_0047_authority`: every row green, authority/installed-assets
   included.
3. `python3 scripts/check_gate_mutations.py --finding 143`: 45 of 45 killed (newproject143-scaffold-not-laid is
   the host's).
4. The consumer suites this sandbox cannot judge, at this branch's head and at ad37b673. They are red on both
   trees here or stop before their rows:
   - 83_veldo_0154_factory_loop, 92_veldo_0088_pm_cycles, 93_veldo_0152_intake_routes, 96_veldo_0204_reservation_policies
   - 106_veldo_0185_dispatch_setup, 71_veldo_0076_projects, 71_veldo_0130_api, 73_veldo_0139_factory_setup
   - 85_veldo_0171_setup_api, 86_veldo_0189_engine_upgrade, 91_veldo_0167_setup_records
   - 94_veldo_0162_configuration_routes, 66_veldo_0051_events, 64_veldo_0050_proof
   - 107_veldo_0153_identity_push, 109_veldo_0161_adoption, 82_veldo_0141_execution_record
   - 85_veldo_0158_credential_delivery
   - 16_warp_1403_sizing_pass and 24_veldo_0007_install_and_run (round 4's list, not run here)

   Suites 83, 92, 93 and 96 drive `Line.run` and `from_line`, and 93 also drives Intake's projects. These are
   the ones to watch.
5. `bash scripts/verify.sh`.
