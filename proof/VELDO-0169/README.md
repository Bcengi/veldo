# VELDO-0169 proof

Implemented from 6512503076f231b94485421f91dc663ee0a36649 on build-veldo-0169; revised in the
review-fix round of review rv169a, from 0a2ba0f9 merged with main.

**The runtime guard.** control_eligibility.Gate.project_problems now answers (refusals, read,
receipt). The receipt exists only when nothing is refused: control_claim.project_check_receipt of the
unit, its project and the versions the check read. The claim organ (control_claim.transition) refuses
a claim, resume or unpark (control_claim.HANDOUTS) without one as missing_evidence:project_check, and
one for another unit or project, or naming a version the writing transaction did not pin and read,
as stale_subject:project_check; nothing is written. The andon's one station contract writer,
Andon.issue_station_contract, applies the same check (control_claim.project_check_problem). Every
handout asks the check again inside its own store transaction: the inbox's resume and unpark writes,
the andon resume's write, and the claim receiver's transaction transition, now registered on the
receiver's own connection. The checks before the transaction stay, and their read versions are
pinned, so a pause or owner change after the check is stale_version. An andon resume race that is
not a project race is stale_subject again. Park, release, renew and use need no receipt.

**The census** (scripts/suites/support/v169_census.py) reads the engine's syntax trees. It follows
every reference to a callable named transition on any receiver, getattr and aliases included, keeps
the calls that can bind the organ's own signature, and refuses a reference that escapes or a bare
registration. It follows every call of the station contract writer and refuses an entity of its
kind written anywhere else. It refuses any getattr, attrgetter or methodcaller it cannot resolve.
Each writer is classified by its enclosing function and by the action followed to where its
parameters are built, narrowed by the guards on the path. A handout writer, and every place that
builds its parameters, must make the Gate's check before it on every path. There is no writer table.

Suite `84_veldo_0169_project_handouts` (renumbered from 82, which main uses), 22 rows:

| Criterion | Rows |
| :--- | :--- |
| AC1 | `census/writers` (no failure, and what AC1 says it finds today); `census/planted`: the reviewer's planted writers and more of their shape, each refused at the planted function: the resume copy dispatched only, with its own write and through the resume's write, a local alias, a renamed attribute, getattr, a plain attribute, a bound-method alias, a dynamic getattr, a bare registration, a minted receipt, a second andon resume, a contract written without its writer, the check inside a branch. |
| AC2, AC3 | The five `resume/`, `dispose/` and `andon/` rows each, unchanged in intent, with active controls. |
| AC4 | `claim/absent`, `claim/null`. |
| Lead decisions | `guard/receipt`: no receipt, another unit's, unpinned reads and an older project version refused at the organ and the station contract writer, with current-receipt controls; `guard/resume-again`: the reviewer's copy wired into OPERATIONS, the dispatch and `_transition` refused at run time (own write: missing_evidence, through the resume's write: stale_subject), the real resume still taking the work; `andon/subject-race`. |

The reviewer's `new-station-contract-kind` plant (a new kind name) is not statically a station
contract and stays green; nothing reads that kind as one.

Sixteen fixture suites that commit claim_operation straight through the organ now carry the Gate's
receipt through scripts/suites/support/v169_claims.py. Suite 71 claims its project-less unit while
it is of an active project and then points it elsewhere; suite 72_veldo_0128 activates the project
its units name.

`red-at-65125030.json`: the current suite and its census against the starting tree: 21 rows red by
assertion; andon/subject-race is green there, since the original behavior is what it restores.
`red-at-0a2ba0f9.json`: against the reviewed commit, census/writers, census/planted, guard/receipt,
guard/resume-again and andon/subject-race red by assertion. Reproduce with
`python3 proof/VELDO-0169/drive.py --red <commit>`.

`mutations.json`: 23 finding-169 mutants with their diffs, a green baseline and a green no-op per
changed module; every named row red by assertion. `validation.json` holds the checks. The canonical
gate is not run and no stamp is claimed; the specification stays ready.
