---
schema: veldo.spec/v1
id: VELDO-0169
title: Every path that hands out work, found by a census of the claim and station contract writers, refuses a unit of a stopped project, and a claim on a unit with no project, with the Gate's one project check
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W129
plan_revision: 4
depends_on: [VELDO-0031, VELDO-0064, VELDO-0075, VELDO-0076, VELDO-0133]
placement: [contracts, engine, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_assignment*.py"
  - ".veldo/control_assignment*.py"
  - "engine/.veldo/control_andon*.py"
  - ".veldo/control_andon*.py"
  - "engine/.veldo/control_claim.py"
  - ".veldo/control_claim.py"
  - "engine/.veldo/control_eligibility*.py"
  - ".veldo/control_eligibility*.py"
  - "engine/.veldo/control_store.py"
  - ".veldo/control_store.py"
  - "engine/.veldo/control_heartbeat.py"
  - ".veldo/control_heartbeat.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0169_*.py"
  - "scripts/suites/support/v169_*.py"
  - "scripts/suites/62_veldo_0039_dispatch.py"
  - "scripts/suites/63_veldo_0040_containment.py"
  - "scripts/suites/63_veldo_0049_floor.py"
  - "scripts/suites/64_veldo_0050_proof.py"
  - "scripts/suites/67_veldo_0041_heartbeat.py"
  - "scripts/suites/67_veldo_0056_candidates.py"
  - "scripts/suites/67_veldo_0135_offers.py"
  - "scripts/suites/72_veldo_0128_reports.py"
  - "scripts/suites/75_veldo_0062_accounts.py"
  - "scripts/suites/78_veldo_0060_claude_adapter.py"
  - "scripts/suites/78_veldo_0160_account_pool.py"
  - "scripts/suites/79_veldo_0061_codex_adapter.py"
  - "scripts/suites/80_veldo_0155_claude_baseline.py"
  - "scripts/suites/81_veldo_0156_codex_baseline.py"
  - "scripts/suites/82_veldo_0129_worker_wiring.py"
  - "scripts/suites/82_veldo_0141_execution_record.py"
  - "scripts/suites/58_veldo_0031_claims.py"
  - "scripts/suites/59_veldo_0031_review.py"
  - "scripts/suites/60_veldo_0064_inbox.py"
  - "scripts/suites/66_veldo_0047_authority.py"
  - "scripts/suites/69_veldo_0133_dispositions.py"
  - "scripts/suites/70_veldo_0069_bindings.py"
  - "scripts/suites/71_veldo_0076_projects.py"
  - "scripts/suites/72_veldo_0075_andon.py"
  - "scripts/suites/73_veldo_0078_backlog.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0169-stopped-project-checks-where-work-is-taken.md"
  - "specs/index.md"
  - "proof/VELDO-0169/*"
behavior_bearing: true
observability:
  logs: >
    Record each refused resume, disposition or claim with the unit, its project, the refusal the Gate's
    project check named, and the record versions it was decided from; record each census run with the
    writers it found and how each is classified.
  metrics: >
    Count resumes, dispositions and claims refused by reason (project_not_active:<state>,
    owner_not_current, missing_authority:project), and writers the census found by class.
  traces: >
    Join each refusal to the assignment, disposition, stop or claim command and the project record
    version it read.
  error_taxonomy: >
    The refusals are the Gate's own names, unchanged: project_not_active:PAUSED, :CANCELED, :COMPLETED,
    :owner_not_current, :not_a_project and missing_authority:project, whether the caller's check or the
    claim organ's and the station contract writer's own check inside the write names them; a pause
    committed after the caller's check and before the write refuses as stale_version. A writer the census
    does not name, a handout writer that does not ask the check, or a claim built outside the claim
    organ, fails the census by the writer's module and function. The store refuses a claim record that
    is not exactly what the claim organ returned in the same transaction as entity_owned, another
    function offered as the organ as foreign_transition, an organ decision or a station contract issued
    outside a command transaction as outside_transaction, and an organ decision in a store where the
    organ was never declared as undeclared_organ; an andon resume race that is not a project race keeps
    stale_subject.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Every engine path that writes a claim or issues a station contract is known, and every one of
      them that hands out work asks the Gate's one project check. Set and completeness: A census scans the
      engine's source (engine/.veldo) for every call of the claim organ's transitions
      (control_claim.transition) and every issue of a station contract, never from a fixed list; today it
      finds the claim receiver (control_claim.Receiver), the assignment resume, release and disposition of
      control_assignment (VELDO-0064, VELDO-0133), the heartbeat's renewal (control_heartbeat), and the
      andon resume's station contract (control_andon). Each writer found is classified in the census as
      handing out work (a claim, a resume, the disposition's backlog outcome that clears a park, a fresh
      station contract), which must call control_eligibility.Gate.project_problems before it writes, or as
      handing out nothing (a release, the renewal of a claim already held), with that reason. The census
      row fails on a writer it does not name and on a handout writer that does not call the check.
      Falsifier: Add to control_assignment a second resume path that writes a claim without the check,
      and the census row must fail on it.
    falsified_by: >
      Add to control_assignment a second resume path that writes a claim without the check, and the census
      row must fail on it.
  - id: AC2
    text: >
      Claim: Resuming a parked unit through its assignment (VELDO-0064), and the backlog outcome of its
      disposition (VELDO-0133), refuse a unit whose project is stopped. Set and completeness: The resume
      and the disposition's backlog outcome ask the shared Gate's project check for the parked unit before
      they write the new claim or clear the park, and pin the project and owner records that check read
      with the transaction's other inputs, as the claim receiver does since VELDO-0076's fix. Drive each
      with the project paused, canceled, completed, with its owner not current, and with a pause committed
      between the check and the write: each is refused by the Gate's name, the last as stale_version, and
      no claim is written and no park is cleared. The disposition's close and other outcomes, which hand
      out nothing, are unchanged. Falsifier: Drop the project check from the resume, and the
      paused-project resume row must fail.
    falsified_by: >
      Drop the project check from the resume, and the paused-project resume row must fail.
  - id: AC3
    text: >
      Claim: Resuming a unit from an andon stop (VELDO-0075) refuses a unit whose project is stopped. Set
      and completeness: control_andon's resume asks the same project check before it issues the fresh
      station contract and pins what it read the same way. Drive it over the same five project states as
      AC2: each is refused by the Gate's name, the stop stays stopped and no contract is issued. Falsifier:
      Drop the project check from the andon resume, and the paused-project andon row must fail.
    falsified_by: >
      Drop the project check from the andon resume, and the paused-project andon row must fail.
  - id: AC4
    text: >
      Claim: The claim receiver refuses a claim on a unit that names no project, as every station refuses
      that unit. Set and completeness: The receiver (control_claim) runs the Gate's project check for
      every claim, not only for a unit whose project field is set, so a unit with no project is refused
      missing_authority:project with nothing written, exactly as the Gate refuses it at a station. The
      suite drives a claim on a unit with no project field, one whose project is null, and one with an
      active project, which is accepted. Every suite that claims a unit through control_claim.Receiver,
      directly or through the authority service (suites 58, 59, 60 of VELDO-0064, 66 of VELDO-0047, 69 of
      VELDO-0133, 71 of VELDO-0076 and 73 of VELDO-0078, found by a grep of the suites), seeds an active
      project for the units it claims. Falsifier: Skip the check when the unit's project is null, as today,
      and the no-project claim row must fail.
    falsified_by: >
      Skip the check when the unit's project is null, as today, and the no-project claim row must fail.
required_evidence: [unit, integration]
rollback: >
  Revert to the earlier resume, disposition and claim paths; the Gate still refuses a stopped project's
  run at its next station, so no stopped project's work is built either way. No automatic rollback is
  authorized.
---

## Intent

When the owner pauses or cancels a project, no path hands out its work again, not only the paths that
run it.

## Context

W129 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 4. The Codex
whole-project review of 2026-09-26 found that a signed claim took a unit of a paused or canceled project,
and the fix landed on main at a4769f68: the claim receiver now asks the Gate's own project check. Its
review (rvfix0926) found the same gap in two more places that hand out work: the assignment resume of
VELDO-0064 writes a fresh claim for a parked unit, and the andon resume of VELDO-0075 issues a fresh
station contract, and neither reads the project's state. The Gate still blocks the run at its next
station, so nothing is built, but the work is handed out and its holder waits on a stopped project. The
same review found the receiver accepts a claim on a unit with no project, which the Gate refuses at every
station (missing_authority:project). The gaps were found one path at a time, so this specification adds a
census of every writer of a claim or station contract: the disposition of VELDO-0133 also hands parked
work out again (its backlog outcome clears the park), and it gets the same single check. This new
specification is draft; authoring it supplies neither implementation proof nor operational activation.

## Out of scope

The Gate's project check itself (VELDO-0076, unchanged); the pause and cancel commands; which outcome
the owner picks for a stopped project's parked work (VELDO-0133's question, unchanged); handing a project
to a new owner (Release 3); test fixtures that write claims straight into the store without a receiver,
which are not engine paths.

## What the reviewer judges

- Normal use: the owner pauses or cancels a project while some of its units are parked on an assignment,
  waiting on a disposition or held at an andon stop, then someone answers the assignment, the disposition
  or the stop; a worker claims a unit.
- Threat model: work of a stopped project handed out by a resume, a disposition or a claim; a new path
  that hands out work without the check; a pause committed between the check and the write missed; a
  unit with no project claimed. The owner's account, the store and the
  Gate are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); forged rows in
  our own store; a project record of another kind planted at the project's id (already refused by the
  Gate as not_a_project).

## Notes

Use the one check. The Gate's project_problems already returns the versions it read so a caller can pin
them, and the claim receiver shows the pattern; a second copy of the rule is the defect this closes. The
census reads the source's syntax tree, so a writer added later is found whether or not anyone lists it.

## History

2026-09-27: new draft from the review rvfix0926 of the Codex-review fixes landed at a4769f68 (items g and
h of its filed list). A draft: only the owner marks a specification ready.

2026-09-27: amended on the independent check of this batch and the lead's decisions. New AC1: a census of
every engine writer of a claim or station contract, each classified as handing out work (which must ask
the Gate's one project check) or handing out nothing, so a path is never missed one at a time again.
VELDO-0133's disposition, whose backlog outcome hands parked work out again, joins the assignment resume
under the same check (AC2), and depends_on adds VELDO-0133. The footprint lists every suite that claims a
unit through control_claim.Receiver (58, 59, 60, 66, 69, 71 and 73, by grep), which AC4 requires to seed
an active project. The title names the census. Still a draft.

2026-09-27: marked ready by the owner (Telegram 29229, "all ready").

2026-09-27: implemented on build-veldo-0169. Assignment resume, backlog disposition and andon
resume use the shared eligibility Gate's project check and pin its project and owner reads;
every claim asks it, including an absent or null project. Suite 82_veldo_0169_project_handouts
scans engine syntax for claim transitions and station contract writers, and drives the three
handout paths over stopped projects and intervening project and owner writes. Its 18 rows are
red by assertion at 65125030. Finding 169 registers the declared falsifiers and read-pin
mutations. The footprint gains scripts/drive.py because the requested proof command did not
exist; it records this suite's red and mutation evidence using the recent proof driver pattern.
Existing claim and andon fixtures now name active projects. Status and approval remain unchanged.

2026-09-27: review-fix round on build-veldo-0169 (review rv169a), with the lead's decisions. The
census did not meet AC1: it tied writers to entry points through a written table and found claim
writers only by receiver name, so a copy of the resume without the check passed it. Now the claim
organ refuses a claim, resume or unpark, and the andon's one station contract writer
(Andon.issue_station_contract) refuses a contract, without the receipt Gate.project_problems makes
when it finds no problem. The receipt names the unit, its project and the versions the check read,
and is accepted only when those are the versions the writing transaction pinned and read; otherwise
the write is refused missing_evidence:project_check or stale_subject:project_check and nothing is
written. Each handout asks the check again inside its own store transaction; the claim receiver
registers its transition on its own connection for that. The census
(scripts/suites/support/v169_census.py) reads every reference to a callable named transition on any
receiver, getattr and aliases included, every call of the station contract writer and every entity
of its kind written elsewhere, follows each writer's action to where its parameters are built, and
requires the check to come before the write and before each such build on every path; a construct it
cannot resolve fails it. An andon resume race that is not a project race is stale_subject again. The
suite is renumbered 84, since main's 82 is taken, and its driver moves to proof/VELDO-0169/drive.py
beside main's scripts/drive.py. The footprint drops scripts/drive.py and gains the census and claim
support modules and the sixteen suites whose fixture claims now carry the receipt. Status and
approval remain unchanged.

2026-09-27: second review-fix round on build-veldo-0169 (review rv169b), with the lead's decisions. The
reviewer found that the project-check receipt was a plain dict any caller could build or rewrite, and
that a transition returning a hand-built claim entity committed a claim on a paused project, since the
claim kind had no store ownership. The receipt is removed: the consumer checks, it trusts no token.
The claim organ (control_claim) now decides every claim in one function, `_decide`, reached through
transition(conn, params, before), itself a store transaction transition: for a claim, a resume or an
unpark it asks Gate.project_problems of the unit on the transaction's own connection while that
transaction holds the write lock, and refuses by the Gate's name with nothing written.
Andon.issue_station_contract does the same inside its command transaction. Callers pass nothing; they
still ask the check first, to name a refusal early and pin what it read. The store gains organ-owned
kinds (control_store.declare_organ and organ_write): the claim organ declares the claim kind when the
claim receiver, the inbox or the heartbeat's renewals attach, and the store writes an entity of kind
claim only when it is exactly what the declared organ returned in the same command transaction, so a
hand-built claim, a generic upsert of one, an organ answer edited on the way out and another function
offered as the organ are refused by name (entity_owned, foreign_transition), and an organ decision
outside a command transaction is refused outside_transaction. The census keeps AC1: it now requires
the check where each handout's parameters are built (or at the write, when they are built there or not
resolved), refuses a claim built outside the claim organ, follows the organ's new signature, and
resolves a module's own method or function named transition as not the organ. New rows of suite 84:
organ/stopped (a paused, canceled, completed and owner-not-current project refuses the organ's claim,
resume and unpark and the station contract writer on paths with no caller check), organ/outside,
organ/ownership, guard/forge (the forge probe's cases) and organ/race (the owner's pause and resume
from a second process while claims run, three rounds, with a delay between the receiver's check and
its write, and through the organ bare); guard/resume-again now drives the reviewer's copies over a
paused project. The fixture suites no longer carry receipts (support/v169_claims.py is removed): they
register the organ as a transaction transition and declare it first. A claim a fixture sets in a state
no transition makes is planted around execute (support/v169_rows.py), as 59_veldo_0037_aliases plants
a revision. Suite 66 takes the launch fixture's claim through the installed organ, suite 79's second
installation reaches the same organ file, and suite 71 reads the receiver's own check and pin
directly, since the organ's own check now refuses those claims too. The footprint gains
control_store.py, control_heartbeat.py and suite 70_veldo_0069_bindings. Filed, not built: the census
does not resolve a callable reached through __dict__['transition'], a kind read as
sys.modules[...].CONTRACT_KIND, or a kind given as another module's attribute (X.KIND); the store's
checks at run time refuse all three. A store that already holds claims written before the organ was
declared refuses the declaration (ownership_conflict), as every first ownership declaration does;
the re-declaration path is Release 2. Status and approval remain unchanged.
