# VELDO-0169 proof

Implemented from 6512503076f231b94485421f91dc663ee0a36649 on build-veldo-0169.

Assignment resume and the backlog disposition call the eligibility Gate's project check,
then pin the exact project and owner versions it returned in the inbox transaction. Andon
constructs that same eligibility Gate on its ingress connection, separately from its channel
Gate, and checks before issuing a station contract. A concurrent pause or owner change
refuses as stale_version. Every claim asks the project check, including units whose project
field is absent or null. Refusal observations retain project identity and read versions;
counters retain refusal names. The three engine assets and installed copies are identical.
No new engine asset needs scaffold registration.

Suite: `82_veldo_0169_project_handouts`, registered with its own prerequisite closure.

| Criterion | Rows and observations |
| :--- | :--- |
| AC1 | `census/writers`: AST scan of all engine Python source finds six writer sites, four handing out work and two handing out nothing. Every site is named by module, function and argument; unknown sites fail. Handout entries reach the shared project check through their own helpers. The census records each classification and reason, with counts. |
| AC2 | `resume/PAUSED`, `resume/CANCELED`, `resume/COMPLETED`, `resume/owner_not_current`, `resume/race`, and the corresponding five `dispose/` rows. Signed commands refuse by the Gate's exact name, preserve claim, park, assignment, unit and backlog records, and record the read versions. Each race row commits both a real pause and, separately, a real owner-role change between check and write; both refuse stale_version. Every row has an active-project control. Close and other still apply on a paused project. |
| AC3 | The same five `andon/` rows, using real raised stops, presented requests and API settlements. Refused resumes preserve the stop and unit and issue no contract. Active controls issue a fresh contract. Project and owner races each refuse stale_version. |
| AC4 | `claim/absent` and `claim/null`: signed claims refuse missing_authority:project, agree with the Gate and write nothing; an active-project claim succeeds beside each. Existing claim and andon fixtures seed active projects. Suites 71 and 73 already did so. |

The suite uses generated OpenSSH keys, real SQLite stores and production project, membership,
claim, inbox, andon, presentation, settlement and intake writers. Accepted unit and backlog
records use the claim organ's admission fixture seam; no claimed, parked, stopped, answered,
settled or project lifecycle record is fabricated. Completion for assignment cases happens
while the claim is held, before opening the assignment, since completion correctly refuses an
outstanding submitted assignment. All channel traffic uses the guarded loopback Bot API.
No model, real login, credential or Telegram service is used.

`red-at-65125030.json` records the current suite against an unchanged git archive of the
starting commit: all 18 rows red by assertion, no exceptions. Reproduce with scripts/drive.py
and its red option naming 65125030.

`mutations.json` records ten finding-169 mutants, the green baseline and one green no-op
copy per changed production module. Each mutant has its exact diff beside the report and
fails its named row by assertion. Names are prefixed handout and unique across the registry:
unlisted resume, unchecked resume, unchecked backlog disposition, unchecked andon resume,
null-project claim bypass, project and owner pins dropped independently from assignment and
andon transactions, and renamed andon stale_version. The first four behavior defects include
every criterion's declared falsifier.

Validation recorded so far:

- New suite: 18 passed; shared preamble: 26 passed.
- Eight affected suites: 181 passed including the preamble, zero failures.
- Those eight plus the new suite under the requested stripped environment: 199 passed,
  zero failures. HOME and TMPDIR are temporary paths in /dev/shm.
- Full selftest and final boundary, footprint, anchor and validator results are recorded below
  after their runs. Partial suite runs are regression observations, not a gate stamp.

The canonical gate is not run, as instructed. No verification stamp is claimed. Independent
review, approval and landing remain the reviewer's work; the specification stays ready.

The first full selftest completed with 6877 passed and one failed row:
`VELDO-0040 containment/exit-notified`. That unchanged row includes an exit-notification
latency bound below 0.75 seconds. Its suite passed unchanged on an immediate isolated rerun:
20 suite rows plus 26 preamble rows, zero failures. The full run is repeated under the
requested stripped environment before completion; no containment code or test is changed.

An additional whole-suite attempt under the stripped environment stopped in the unchanged
`12_warp_1210_hardening_four` fixture at `_m10_r12_fifo_at`: PYTHONDONTWRITEBYTECODE prevented
the cache directory that its FIFO fixture assumes a warming subprocess creates. This was a
FileNotFoundError, not a VELDO-0169 assertion failure. The required nine selected suites passed
under that environment. The full rerun keeps ordinary bytecode behavior and uses /dev/shm for
temporary files. No legacy fixture is modified.
