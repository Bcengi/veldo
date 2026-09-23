# VELDO-0053 proof

Architecture failure handling at every eligibility entry, Release 1 stage 1 of PLAN-0019 revision 3
(W38). Branch `build-veldo-0053`, built on main acd877c. Specification status, policy and every other
specification are unchanged; the specification gained one footprint line and a History line for the
mutation driver.

## What landed

**One predicate, every station.** `.veldo/control_eligibility.py` (mirrored byte-identically in
`engine/.veldo/`) adds `architecture_accepted` to the predicates of every floor station (selection,
claim, direct execution, build, review, publication and provider request), asked right after current
admission. Because VELDO-0052's registrations all decide through the one `Gate`, every registered entry
(frontier, work loop, plan run-check, the executor's station and call decisions, the dispatcher's build,
review and publication, and `CallHandle.invoke`) now refuses by name when the architecture refuses. No
entry module changed.

**The installed validator.** The Gate loads `validate.py` from its own directory, the installed engine,
never the copy a workspace carries, and asks its `validate_checks.entry_contract` for the workspace's
`.veldo/architecture.yaml`. That entry runs VELDO-0016's one tri-state loader with the installed
structural validator and parser, and returns the source file of each function that judged the contract.
The decision records those files (resolved path and digest) and the artifact it judged (path, file
type, digest; only a regular file is opened, so a FIFO is never read).

**The accepted artifact.** The authority's record `architecture:<repository>` (state `accepted`, the
sha256 digest of the accepted bytes) makes the contract required whatever the workspace's own policy
says, and the workspace file must be exactly those bytes. Without a record the repository's policy flag
decides absence, as VELDO-0016's loader always has. The record is a normal consumed input, so a
re-acceptance after selection is `stale_input:architecture` through VELDO-0052's tickets.

**Named refusals.** `missing_evidence:architecture/required_absence`,
`invalid_input:architecture/unreadable`, `invalid_input:architecture/parse_failure`,
`invalid_input:architecture/invalid_structure`, `missing_authority:architecture/unaccepted_artifact`,
`missing_authority:architecture` (a record not accepted or naming no sha256 digest),
`missing_evidence:architecture/workspace` (a store-only Gate facing an accepted record) and
`unavailable_service:architecture_validator` (a validator that raises). None maps to unknown or
success. `enrolled_gate` passes the workspace it verified, so every production Gate judges a file.

## Criteria, rows and driven mutations

Suite `scripts/suites/60_veldo_0053_architecture.py`, 13 rows: 8 assertions and 5 `ran/` rows, one per
region, which stay green under every mutation, so each red row below failed its assertion with its region
completing. A temporary Git repository is both the workspace and the installed `.veldo`; a second tree is
a clone with its own `.veldo` whose `arch.py` is a success stub that writes a marker file when loaded.
One unit passes every other predicate at every station, so each refusal is the architecture's.

All 14 mutations are registered as finding 53 in `scripts/check_teeth_mutations.py`, applied to a
temporary copy, and each turned its named rows red while the unmutated copy (the driver's baseline run
of the same suite) was green with 39 assertions (`mutations.json`, each diff in `mutations/`).

**AC1, valid, absent and invalid contracts.** Rows `architecture/state-kinds` and
`architecture/ready-refusal`. Nine real-file states: valid, optional absent, required absent (policy
`architecture_contract: required`), unreadable (chmod 000, the denial observed on open under the running
worker), malformed (a top-level list, and text outside the parser subset), and wrong type (a directory,
a FIFO, and a mapping with wrong-typed fields). `state-kinds` compares the installed loader's kind with a
table written in the suite, and runs the installed validator as a real process (`validate.py arch`) over
every present state: exit 0 only for valid. `ready-refusal` drives the ready transition
(`check_ready`) and all seven station decisions under the policy, then again under an accepted record
naming the bytes present: valid and optional absence proceed, everything else refuses with the kind's
named code, and under an accepted record absence is required absence. A store-only Gate with no record
proceeds.
- Declared falsifier `architecture-malformed-as-optional-absence` (the Gate reads a present malformed
  contract as optional absence): red `ready-refusal`.
- Second mutations `architecture-loader-malformed-as-absence` and
  `architecture-loader-wrong-type-as-absence` (the shared loader answers absence for a malformed
  contract, or for anything that is not a regular file): red `ready-refusal` and `state-kinds`.

**AC2, every enabled entry blocked.** Rows `architecture/registrations`,
`architecture/entries-blocked` and `architecture/forbidden-review-launch`. One driver per entry of
`EL.REGISTRATIONS`, the set required equal to the registrations, each run under a valid accepted
contract (every entry launches: the control), an invalid accepted contract (the accepted bytes present
and structurally invalid) and a required missing one (accepted, deleted, the workspace policy saying
optional, so VELDO-0016's own file check stands down and only the Gate refuses). Under both failures no
entry offered, claimed, built, reviewed, landed or called; the claim ledger, the store's claim records,
the call receiver, the opened worker slots and the trunk (HEAD and every ref) are identical before and
after, and every entry that reports names the refusal. The executor's review registration needs its
build first: that build runs against the valid contract, the architecture turns invalid or goes missing
during it, and the review station refuses before any reviewer (its one build is counted apart).
- Declared falsifier `architecture-review-skipped` (the review station drops the predicate): red
  `forbidden-review-launch` (the dispatcher's direct review launched its reviewer), and every row that
  asserts all stations.
- Second mutation `architecture-review-decision-skips` (the review decision skips the predicate at
  decision time): red `forbidden-review-launch`.
- Further: `architecture-invalid-structure-passes` red `entries-blocked`;
  `architecture-record-not-required` red `entries-blocked` and `substitution`;
  `architecture-provider-request-unasked` red `registrations` and `entries-blocked`.

**AC3, the installed validator and the accepted artifact.** Row `architecture/substitution`. The
installed Gate over the clone: architecture deleted (clone policy weakened to optional), weakened (a
structurally valid contract with another area and version, not the accepted digest), accepted but
structurally invalid (the stub would pass it), and accepted valid. The first three refuse at every
station with required absence, unaccepted artifact and invalid structure, and the installed dispatcher's
review launches no reviewer; the fourth proceeds and reviews. Every decision's recorded validator files
are the installed ones by resolved path and digest, the artifact is the clone's file with the digest of
its bytes (none when deleted), and the stub's marker never appears (`observations.json`,
`substitution`).
- Declared falsifier `architecture-clone-validator` (the Gate loads the workspace's validate.py): red
  `substitution`.
- Second mutations `architecture-accepted-digest-ignored` and `architecture-identity-from-workspace`
  (the recorded identity names what the workspace carries): red `substitution`.

**Record states and observability.** Rows `architecture/record-states` (a withdrawn record, one naming
no digest and one naming a non-sha256 digest refuse `missing_authority:architecture`; a store-only Gate
facing an accepted record refuses `missing_evidence:architecture/workspace`) and
`architecture/observations` (every decision's event carries basis, kind, artifact digest and the
installed validator digests; architecture refusals keep the invalid input, missing evidence and missing
authority taxonomy; counts of accepted and refused). Driven by `architecture-unaccepted-record-accepted`,
`architecture-store-only-passes` and `architecture-identity-not-recorded`.

## Narrowest seams, stated

- **The accepted architecture record.** Nothing on main writes `architecture:<repository>`; the owner's
  acceptance of a contract revision is not built. The suite writes the plain entity through the real
  store, as VELDO-0052's suite writes admission and plan records.
- **Reaching the installed entry.** `validate.py`'s re-export list is VELDO-0016's and outside this
  footprint, so the Gate calls `entry_contract` on `validate.py`'s own `validate_checks` instance (its one
  parser bound) rather than on a new re-exported name.
- **The loader registry.** `policy_contract.LOADER_ADAPTERS` is outside this footprint and suite 29 pins
  its 17 rows, so the new entry adds no row. The loader call lives in `validate_checks.py`, a module the
  registry already covers, and `control_eligibility.py` calls no loader name, so the registry scan stays
  exact. A row for `validate_checks.entry_contract` is a follow-up for VELDO-0016's registry.
- Not isolated: the executor's `_decide_calls` registration is always preceded by its station decision,
  which asks the same predicate first, so its driver shows the refusal of that earlier decision. Under
  `architecture-review-skipped` the executor's review still refuses at its provider-request boundary;
  the dispatcher's direct review is the launch the declared falsifier turns red.
- Release 2, not added: a race between the bytes validated and the bytes digested, and concurrent
  architecture inputs. Running the suite as root cannot deny a read, so `state-kinds` would red there
  rather than pass without the denial.

## Cost and verification

Suite 60_veldo_0053 runs in about 1.3 s (`observations.json`, `suite_seconds`), including seven
installed-validator processes run in sequence. `--finding 53` drives 14 mutations in 38 s here (28 suite
runs), about 5 s of wall time in the gate's 8-worker mutation stage. Targeted checks on this branch:
`python3 -B scripts/selftest.py --suite 60_veldo_0053_architecture` (13 rows, 39 assertions with the
shared preamble, 0 failed), `python3 -B scripts/check_teeth_mutations.py --finding 53` (14 rejected),
`--finding 52` (47 rejected, unchanged by the new predicate), suites 60_veldo_0052, 29_veldo_0016,
08, 17 and 21 green, `python3 .veldo/validate.py all` (exit 0), `bash scripts/check_generated.sh` and
`bash scripts/check_template_sync.sh` (pass). The full gate is run by the lead.

`drive.py` regenerates `observations.json` from one run of the suite.
