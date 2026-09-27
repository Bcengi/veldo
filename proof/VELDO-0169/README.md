# VELDO-0169 proof

Implemented from 6512503076f231b94485421f91dc663ee0a36649 on build-veldo-0169; revised in the
review-fix round of review rv169a (from 0a2ba0f9) and again in the round of review rv169b (from
6d2f40a7).

**The claim organ checks, it trusts no token.** The receipt of the first round is gone. Every claim
record is decided by one function of control_claim, `_decide`, reached through
`transition(conn, params, before)`, which is itself a store transaction transition. For a claim, a
resume or an unpark (control_claim.HANDOUTS) it asks control_eligibility.Gate.project_problems of the
unit on the transaction's own connection while that transaction holds the write lock, and refuses by
the Gate's own name with nothing written. Andon.issue_station_contract does the same inside its
command transaction. Callers pass nothing. They still ask the same check before they build the
command, to name the refusal early and to pin the project and owner records it read, so a pause or
owner change after that check is stale_version. Park, release, renew and use are not checked.

**The store owns the claim kind through its organ.** control_store gains organ-owned kinds:
`declare_organ` persists that one function (its qualified name, its module file and that file's
sha256) decides every entity of a kind, and `organ_write` runs that function inside the open command
transaction and records what it returned for that transaction only. Execute refuses entity_owned for
any claim record that is not exactly what the organ returned in the same transaction: a claim built by
hand, a generic upsert of one, the organ's answer edited on the way out. Another function offered as
the organ is foreign_transition; an organ decision outside a command transaction is
outside_transaction; one in a store where the organ was never declared is undeclared_organ. The
claim receiver, the assignment inbox and the heartbeat's renewals declare the organ when they attach.

**The census** (scripts/suites/support/v169_census.py) still reads the engine's syntax trees for every
reference to a callable named transition on any receiver (getattr, aliases and imports included),
every call of the station contract writer and every entity of its kind. It now follows the organ's
three-argument signature, refuses any claim entity built outside control_claim, and resolves a
module's own method or function named transition as not the organ. A handout's parameters must be
built after the Gate's check on every path through the function that builds them, and where they are
built at the write itself or are not resolved, the write's own function must ask it.

Suite `84_veldo_0169_project_handouts`, 26 rows:

| Criterion | Rows |
| :--- | :--- |
| AC1 | `census/writers`; `census/planted`: the reviewer's planted writers and more of their shape, each refused at the planted function (the resume copy dispatched only, with its own write and through the resume's write, a local alias, a renamed attribute, getattr, a plain attribute, a bound-method alias, a dynamic getattr, a bare registration, a claim built by hand, a registered lambda building one, a second andon resume, a contract written without its writer, the check inside a branch). |
| AC2, AC3 | The five `resume/`, `dispose/` and `andon/` rows each, with active controls. |
| AC4 | `claim/absent`, `claim/null`. |
| Lead decision 1 | `organ/stopped`: a paused, canceled, completed and owner-not-current project refuses the organ's claim, resume and unpark and the station contract writer, on paths with no caller check and nothing passed, with active controls; `organ/outside`; `organ/race`: the owner pauses and resumes the project from a second process while claims run (three rounds, a delay between the receiver's check and its write, and through the organ bare), and the journal shows no claim written while the project was not ACTIVE; `guard/resume-again`: the reviewer's resume copies over a paused project, refused by the organ. |
| Lead decision 2 | `organ/ownership`: the declaration held by the store, and a claim built by hand, a generic upsert, an edited organ answer and a foreign organ refused by name, with a control; `guard/forge`: the forge probe's cases on a paused project (a literal project check, another unit's rewritten check, a hand-built claim entity) refused. |
| VELDO-0075 | `andon/subject-race`. |

Fixture suites no longer carry receipts (support/v169_claims.py is removed). They register the organ
as a transaction transition and declare it first. A claim a fixture sets in a state no transition
makes is planted around execute (support/v169_rows.py). Suite 66 takes its launch fixture's claim
through the installed organ, suite 79's second installation reaches the same organ file, and suite 71
reads the receiver's own check and pin directly.

`red-at-65125030.json`, `red-at-0a2ba0f9.json`, `red-at-6d2f40a7.json`: the current suite and its
census against the starting tree and against both reviewed trees, every failing row red by
assertion. At 6d2f40a7 the organ has the receipt interface, so the rows driving the organ's new
signature red on its refusal to be called that way; the hand-built claim and the generic upsert of one
are accepted there, which is the reviewer's second finding. Reproduce with proof/VELDO-0169/drive.py
and its red option naming the commit.

`mutations.json`: finding 169's mutants with their diffs, a green baseline and a green no-op per
changed module; every named row red by assertion. `validation.json` holds the checks. The canonical
gate is not run and no stamp is claimed; the specification stays ready.
