# VELDO-0143 round 4: the round 3 review's findings

Branch agent/claude/veldo-0143. The review is `../REVIEW-claude-r3-2026-10-23.md`, added as written in 6dc66026.
Round 4's code is final at 15ef0204; 1d636d1f re-anchors two round-3 mutations. c918f776 adds DECISIONS 23 and 24 and the specification's footprint and
history, and this evidence follows. Nothing here is a gate result, a review verdict or an approval.

This sandbox refuses AF_UNIX, has no systemd user manager, and may not write the account's graph stage. So suite
110 runs here through `../round2/sandbox_run.py --stage --agent`, with the graph stage and the recording SSH
agent stood in. The full gate (`scripts/verify.sh`) cannot run here.

## Results here

- Suite 110 at c918f776 (`110-head.json`): 69 passed. Red: service/hand-off (AF_UNIX, the host's) and
  activation/first-unit (open, pending the owner's decision on VELDO-0188; below).
- Suite 110's round-4 rows on the round-3 engine (`110-round3-engine.json`): the tree is 15ef0204 with the four
  changed `.veldo` modules (control_workflow_cycle_pm, control_service, control_service_projects,
  control_project_proposal) taken from 2ac953ea. It ran as the scratch commit object bf5a29f1, which no branch
  names. Result: 66 passed. Red: activation/factory-line-kept, activation/factory-line-restart,
  proposal/correction-negated, service/hand-off and activation/first-unit. Each new row fails without its fix,
  and it fails in the way the review describes:
  - The factory line's take is refused `no_such_feature`.
  - The new line is retried and faults on every pass.
  - After a restart, the factory line's cycles fault.
  - The negated identity and the negated visibility settle.
- Finding 143, `../run_falsifiers.py` in worker mode, no stand-ins: 36 registered, 35 killed here. Each target
  row is red on its mutant. `newproject143-scaffold-not-laid` is not judged here: its row, suite 66
  authority/installed-assets, needs the user manager. The baseline before and after is red only on
  service/hand-off, pm/new-project-run (the graph stage, which worker mode does not stand in) and
  activation/first-unit. The run came in two parts:
  - `falsifiers-143-first19.log` (archive of 15ef0204): the first 19 cases, 18 killed. The driver then stopped,
    because R3-2's rewrite had moved the anchors of newproject143-correction-identity-unbound and
    -visibility-unbound.
  - `falsifiers-143-rest.json` (archive of 1d636d1f): those two anchors now point at R3-2's checks (1d636d1f), and
    the remaining 17 cases are each killed, round 4's five among them. The 19 earlier cases' modules and rows are
    the same at 15ef0204 and 1d636d1f.
  - `falsifiers-r3-1-first.json` (45858ddd): the first run of the R3-1 mutations, each killed.
- Consumer suites (`consumer-suites.json`, `../round2/consumer_suites.py`): 2ac953ea compared with c918f776, one
  after the other on `git archive` trees, the 36 suites of round 3's list: all 36 give the same result on both trees (the same table count and the same red rows). Suites 16 and 24 (round 3 ran them on clones) were not run here and are on the host list.

## Each finding: fix, row, falsifier

| Finding | Fix | Row (red without the fix) | Registered mutation, here |
| --- | --- | --- | --- |
| R3-1 high | `from_line` is failure-atomic. It attaches the once-only owners first (`control_alias.attach`, then `control_readset.attach`, handed to `ProjectCycles`) and builds the inbox, backlog, team, intake and grooming owners only after that. A build that raises puts the connection's registrations back. `Line.build_cycles`: no other line builds cycles while the factory line wants cycles it has not built, so the uuid order does not matter. Another line's refused build is a fault once (`pm_cycles:<code>`) and is not tried again. The activation step puts back the owners it registered, and only then adds the line | activation/factory-line-kept: a pass builds the factory line's cycles; the pass activates `kestrel` with the loop attached (its uuid sorts before the factory's); two loop passes follow. The factory line keeps the same cycles, and the registry's backlog, team and snapshot transitions are its own. Its backlog `take` of a RAW feature of its own repository is accepted, with the item in that repository. The new line is refused once, `invalid_registration`, and is not tried again. activation/factory-line-restart: a new service and loop on the store, every taken-on repository with a line from the constructor, each sorting before the factory's. At both passes the factory project's cycles run on the factory line, with its owners on the connection, and its take is accepted. No other line holds cycles | newproject143-cycles-owners-after (the round-3 order in from_line): killed, both rows. newproject143-refused-cycles-retried: killed. newproject143-factory-owners-taken (no deferral): killed (restart row). newproject143-activation-owners-left: killed |
| R3-2 medium | `mentions`/`affirmed`/`negated` in control_project_proposal. A changed identity or visibility counts only where his words name exactly that one value and no negator (not, no, never, nor, without, instead of, rather than, a word ending n't) stands before it in its clause. A shown identity or visibility he negates does not stay | proposal/correction-negated: the review's words "not under bcengi please, and keep it private, not public" read as bcengi/public fail `invalid_input:correction:identity`. A shown bcengi kept after "not under bcengi, use personal" fails the same way. personal/public after "under personal please, keep it private, not public" fails `:visibility`. The affirmed readings (personal/private, and personal) settle as he said them. Nothing reaches GitHub, and no second question is asked | newproject143-negation-ignored: killed |

The `newproject143-line-not-added` anchor follows the activation's new shape. The line is added after the
connection is put back. That mutation is still killed.

## Choices, recorded in DECISIONS.md

- 23: two choices go beyond the review's two files.
  - The activation step's own Teams and Intake replaced the factory line's team and intake owners (Teams with
    requester `pm`). It now puts the connection's registrations back.
  - A refused build no longer ends the line's part of the pass. Its units are still offered through its own
    Runner.
- 24: the review gives the rule as "immediately before". Taken literally, strict adjacency misses the review's
  own first clause ("not under bcengi"). It also misses "don't make it public". So the window is the clause.
  "nor" and the n't contractions are added to the review's list of negators. A shown value he negates does not
  stay. The limits of a textual binding are listed in entry 24.

## activation/first-unit (open, unchanged in intent)

It is red here on its first part only: the new line's project cycles cannot be built beside the factory line's
on the service's one connection (`invalid_registration: connection already has an allocation authority`). That
is VELDO-0188's job. The AC3 text is unchanged. With R3-1's change the refused build no longer stops the line's
offers. So the row's other parts are green here: the unit is offered on the new line and dispatched through its
Runner, its packet names the new repository and its build follows that repository's commit, and its commit is
authored and committed by the identity alone. Part 1 stays red until the owner decides whether AC3's
first-unit observation moves to VELDO-0188.

## Host runs

1. `python3 scripts/selftest.py --suite 110_veldo_0143_new_project`: every row green except
   activation/first-unit (red on its first part, named). This includes service/hand-off,
   provision/signing-no-agent with its recording socket, pm/new-project-run, and the three round-4 rows.
2. `python3 scripts/selftest.py --suite 66_veldo_0047_authority`: every row green, authority/installed-assets included.
3. `python3 scripts/check_gate_mutations.py --finding 143`: 36 of 36 killed (newproject143-scaffold-not-laid is
   the host's).
4. `python3 scripts/check_gate_mutations.py --finding 161`: 57 of 57 (VELDO-0161 round 9), not re-run here.
5. Each consumer suite this sandbox cannot judge, at this branch's head and at 2ac953ea (or at 928918a5).
   These are red on both trees here, or they stop before their rows:
   - 106_veldo_0185_dispatch_setup, 66_veldo_0047_authority, 71_veldo_0076_projects, 71_veldo_0130_api
   - 73_veldo_0139_factory_setup, 83_veldo_0154_factory_loop, 85_veldo_0171_setup_api, 86_veldo_0189_engine_upgrade
   - 91_veldo_0167_setup_records, 92_veldo_0088_pm_cycles, 93_veldo_0152_intake_routes
   - 94_veldo_0162_configuration_routes, 96_veldo_0204_reservation_policies, 66_veldo_0051_events, 64_veldo_0050_proof
   - 107_veldo_0153_identity_push, 109_veldo_0161_adoption (four AF_UNIX rows), 24_veldo_0007_install_and_run (nested gate)
   - 16_warp_1403_sizing_pass

   Suites 83, 92, 93 and 96 drive `Line.run` and `from_line` directly. They are the ones to watch for R3-1.
6. `bash scripts/verify.sh`: red until activation/first-unit is decided.
