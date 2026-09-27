# VELDO-0169 proof

Implemented from 6512503076f231b94485421f91dc663ee0a36649 on build-veldo-0169; revised in the
review-fix rounds of reviews rv169a (from 0a2ba0f9), rv169b (from 6d2f40a7) and rv169c (from
d22c687e).

**The store holds the invariant, in its commit path.** A transaction that writes a claim record
handing out work (control_store.claim_handout: a new holder, a parked unit taken again, or a park
cleared, which makes the unit claimable) is refused, whole, by the Gate's own name when
control_eligibility.Gate.project_problems finds a problem for any unit the record names: its unit_id
before and after the write, and every execution unit its id can name. The store asks the check
itself (control_store.handout_problem), on the transaction's own connection, after the transition's
records are written and before the journal record is signed, so it reads exactly the state the
transaction commits. It trusts no caller and no attribute and binds nothing to any module's bytes:
the claim organ, a transition that builds a claim by hand, one that sets conn.organ_writes, and the
generic upsert_entity are all held to it, and a store written by earlier code attaches unchanged. The
renewal of a claim already held (the same record with a new heartbeat), a release and a park pass
unchanged. The store loads the Gate by a literal file name on the first handout, so the installer's
closure includes it.

**The claim organ keeps its own check.** control_claim.transition(conn, params, before), a store
transaction transition, asks the same check for a claim, a resume or an unpark
(control_claim.HANDOUTS) on the transaction's connection before any other reason, and refuses by the
same name. Andon.issue_station_contract does the same inside its command transaction. Callers still
ask the check first, to name the refusal early and to pin the project and owner records it read, so a
pause or owner change after that check is stale_version. The claim-kind ownership of the second round
(control_store.declare_organ, organ_write, the entity_organs table, conn.organ_writes) is removed.

**The census** (scripts/suites/support/v169_census.py) reads the engine's syntax trees for every
reference to a callable named transition on any receiver (getattr, aliases and imports included),
every call of the station contract writer and every entity of its kind, follows the organ's
three-argument signature, refuses any claim entity built outside control_claim, and requires a
handout's parameters to be built after the Gate's check on every path through the function that
builds them.

Suite `84_veldo_0169_project_handouts`, 27 rows:

| Criterion | Rows |
| :--- | :--- |
| AC1 | `census/writers`; `census/planted`: the reviewer's planted writers and more of their shape, each refused at the planted function. |
| AC2, AC3 | The five `resume/`, `dispose/` and `andon/` rows each, with active controls. |
| AC4 | `claim/absent`, `claim/null`. |
| The organ's check | `organ/stopped`: a paused, canceled, completed and owner-not-current project refuses the organ's claim, resume and unpark, the station contract writer, and a hand-built claim, resume and unpark, on paths with no caller check, and the organ names the project before any other reason; active controls. `organ/outside`: the station contract writer outside a command transaction. `organ/race`: the owner pauses and resumes the project from a second process while claims run, and the journal shows no claim written while the project was not ACTIVE; a check from an earlier transaction never decides a later one. `guard/resume-again`: the reviewer's resume copies over a paused project. |
| The store's invariant | `store/invariant`: the reviewer's inject probe, a claim built by hand, the generic upsert, a hand-built resume and unpark, a record whose id names a paused unit and whose fields an active one, and one transaction that moves a unit into a paused project and claims it, all refused by the Gate's name with nothing written; a renewal and a release of a claim held before the pause pass; a hand-built claim of an active project is written. `guard/forge`: the forge probe's cases. `store/upgrade`: the reviewer's upgrade probe, a store holding held, released and parked claims as main's organ wrote them on units with no project (support/v169_rows.py plants them), which the claim receiver and the inbox attach to, whose held claim is renewed and released, and whose unit takes a new claim only once its project is active. |
| VELDO-0075 | `andon/subject-race`. |

`red-at-65125030.json`, `red-at-0a2ba0f9.json`, `red-at-6d2f40a7.json`, `red-at-d22c687e.json`: the
current suite and its apparatus against the starting tree and every reviewed tree, every failing row
red by assertion. At d22c687e the claim-kind ownership refuses the hand-built records by entity_owned
where the rows now expect the Gate's name, the organ refuses the upgrade store's receiver
(ownership_conflict), and a hand-built claim of an active project is refused. Reproduce with
proof/VELDO-0169/drive.py and its red option naming the commit.

`mutations.json`: finding 169's mutants with their diffs, a green baseline and a green no-op per
changed module; every named row red by assertion. The third round removes the four mutants of the
removed ownership (organ-write-outside-transaction, store-claim-ownership-dropped,
store-organ-content-ignored, store-organ-origin-unchecked) and adds store-invariant-skipped,
store-invariant-ignores-resumes, store-reads-outside-transaction and store-id-unit-unchecked.
`validation.json` holds the checks. The canonical gate is not run and no stamp is claimed; the
specification stays ready.
