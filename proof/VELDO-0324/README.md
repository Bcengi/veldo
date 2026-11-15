# VELDO-0324 proof

The targeted evidence covers the four acceptance criteria with 18 ticket rows and
seven applied falsifiers. This is partial verification. Criteria stay pending for
the lead's full gate and independent review.

Batch discard sends an item-naming event through the existing Signal and removers.
Its result records each deferral on the batch. No supplied ledger means no batch
removal. Malformed locators signal nothing. The owner and owner_keep mark remain
those of the recorded item. Clean repository removal writes and verifies kept refs
in the main repository; failed saves and unsaved files hold the batch. The existing
keeper and signature suites are also run.

An observation folder is evidence under the accepted VELDO-0302 creator. It keeps
that kind here, and Signal keeps its proof at run finished. The removable folder
case is exercised with declared scratch as well. This does not reclassify evidence
as scratch to satisfy an older description of the batch observation folder.

With the run's space label, the launcher requires a supplied ledger and one present
scratch parent at TMPDIR owned by that run. It copies the complete owner from the
parent, declares before creating, holds its scratch lock, and restores directory
access before releasing the lock. It never deletes recorded scratch. The run event
uses the existing folder remover. Nested repositories, an unsettled borrowed login
and owner Keep hold the scratch. Without the space environment, its own end still
removes its own scratch. No launch deletes another launcher's scratch by age.

Fixture boundaries:

- Files, chmod, locks, git, the journal-backed ledger, real owner enrollment and
  signature checks are real. The open-file row starts a real process and exposes
  only that process to the fixture process table. No real engine is asked anything.
- The future agent-repository lifecycle at run finished is a copy of the registry
  with one fixture cell. VELDO-0347 production lifecycle work is not included. The
  real act prerequisite refusal is checked before fixture callbacks allow removal
  tests. Nothing enables act on an installation.
- The confined command is replaced at prepared_launch. The real launcher, its
  declaration and error paths, permissions and locks run. No service startup wiring
  or real confined worker execution is claimed. A labelled launch without wiring
  refuses before creating scratch. VELDO-0302 uses the same supplied-ledger seam.
- Batch observation evidence is planted and kept. The declaration of observations
  is separately exercised by the unchanged VELDO-0302 suite.
- The older sandbox suites' age expectations now agree with AC3. The lightweight
  borrowed-login suite passed. The runtime suite 102 is left for the lead's heavy
  gate; its live confinement rows were not run here. Suite 86 and captures were
  untouched.

Reproduction: python3 proof/VELDO-0324/run_checks.py tests runs the seven targeted
suites. Its fast argument runs validation, docs, template sync, lint, generated-file
and git-boundary checks. Each suite's exit 2 is the repository's partial-run
convention; tests.json records its actual pass and fail counts.

python3 proof/VELDO-0324/run_falsifiers.py applies each case once in its own temporary
copy. The baseline must be green, and every designated row must turn red. Definitions
are also registered in scripts/check_teeth_mutations.py for the lead's gate. This
proof did not run that stage. The receipts contain small summaries and source hashes.

The lead's exact verification command is ./scripts/verify.sh through the gate lock.
No full gate, heavy suite, teeth stage or policy check was run by this builder.

Fix round 2 (2026-11-15, after the re-review). The ends_on option on the ledger's
declare, the creator seam and the batch is removed; those ledger and seam files are
back to their content before the first fix round. The batch observation folder keeps
the evidence kind's default end list from the kind registry. Row ac1/observation-end
asserts that the folder is evidence, is kept with its proof file after discard, and
that verdict_recorded, ticket_ended and project_ended are all on its list. Row
safety/no-end-option asserts that declare takes no end list from its caller; it
replaces safety/invalid-end-events. The registry holds 20 cases for this finding;
falsifier-cases.json is generated from it, falsifiers.json is this script's rerun,
tests.json and the suite logs are reruns, and teeth.log is the teeth stage's own
output for --finding 324, run last with no edits during it. The earlier statements
above about seven falsifiers and no teeth stage describe the first proof round.
