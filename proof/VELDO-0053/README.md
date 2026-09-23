# VELDO-0053 proof

Architecture failure handling at every eligibility entry, Release 1 stage 1 of PLAN-0019 revision 3
(W38). Branch `build-veldo-0053`, built on main acd877c and merged with main at 07c7557. Specification
status, policy and every other specification are unchanged; the specification gained footprint lines,
each with a History line: the mutation driver, and for the 2026-09-23 review fixes suite 60_0052,
validate.py and contract_loader.py (and their engine copies; arch.py was already in the footprint).

## What landed

**One predicate, every station.** `.veldo/control_eligibility.py` (mirrored byte-identically in
`engine/.veldo/`) adds `architecture_accepted` to the predicates of every floor station (selection,
claim, direct execution, build, review, publication and provider request), asked right after current
admission. Because VELDO-0052's registrations all decide through the one `Gate`, every registered entry
(frontier, work loop, plan run-check, the executor's station and call decisions, the dispatcher's build,
review and publication, and `CallHandle.invoke`) now refuses by name when the architecture refuses. No
entry module changed.

**The installed validator, loaded once.** Each Gate builds one `ValidatorSnapshot` of the engine
installed beside it, never the copy a workspace carries: every engine module is read once into memory
and executed from those bytes, compiled into a fresh module object with the same name and `__file__` as
loading from the installed path gives, and each sibling a module loads by path resolves to the in-memory
bytes of that sibling. Nothing is written to or loaded from disk, so no file can be swapped between the
digest and the code that runs (2026-09-23 second review, below). The snapshot keeps one
structural validator (arch.py) instance for every contract and asks validate.py's PUBLIC `entry_contract`
(re-exported on validate.py, with `entry_validator`), which runs VELDO-0016's one tri-state loader. Every
decision records the snapshot's identity, the installed path and the digest of the bytes loaded for
validate.py, validate_checks.py, contract_loader.py, arch.py and yamlish.py, never a fresh read of the
files on disk; and the artifact it judged (path, file type, and the loader's digest).

**The accepted artifact.** The authority's record `architecture:<repository>` (state `accepted`, the
sha256 digest of the accepted bytes) makes the contract required whatever the workspace's own policy
says, and the workspace file must be exactly those bytes. Without a record the repository's policy flag
decides absence, as VELDO-0016's loader always has. The record is a normal consumed input, so a
re-acceptance after selection is `stale_input:architecture` through VELDO-0052's tickets. The digest
compared with the record is the loader's own: `arch.read_contract` reads the file once, as bytes, and the
loader hands the digest of the very bytes it parsed to its caller (`digested`), so a writer landing
between the read and the comparison cannot make the Gate pass bytes it did not validate.

**Named refusals.** `missing_evidence:architecture/required_absence`,
`invalid_input:architecture/unreadable`, `invalid_input:architecture/parse_failure`,
`invalid_input:architecture/invalid_structure`, `missing_authority:architecture/unaccepted_artifact`,
`missing_authority:architecture` (a record not accepted or naming no sha256 digest),
`missing_evidence:architecture/workspace` (any Gate built with no workspace, record or no record) and
`unavailable_service:architecture_validator` (a validator that raises). None maps to unknown or
success. `enrolled_gate` passes the workspace it verified, so every production Gate judges a file.

## Criteria, rows and driven mutations

Suite `scripts/suites/60_veldo_0053_architecture.py`, 21 rows: 12 assertions and 9 `ran/` rows, one per
region, which stay green under every mutation, so each red row below failed its assertion with its region
completing. A temporary Git repository is both the workspace and the installed `.veldo`; a second tree is
a clone with its own `.veldo` whose `arch.py` is a success stub that writes a marker file when loaded.
One unit passes every other predicate at every station, so each refusal is the architecture's.

All 22 mutations are registered as finding 53 in `scripts/check_teeth_mutations.py`, applied to a
temporary copy, and each turned its named rows red while the unmutated copy (the driver's baseline run
of the same suite) was green with 47 assertions (`mutations.json`, each diff in `mutations/`).

**AC1, valid, absent and invalid contracts.** Rows `architecture/state-kinds` and
`architecture/ready-refusal`. Nine real-file states: valid, optional absent, required absent (policy
`architecture_contract: required`), unreadable (chmod 000, the denial observed on open under the running
worker), malformed (a top-level list, and text outside the parser subset), and wrong type (a directory,
a FIFO, and a mapping with wrong-typed fields). `state-kinds` compares the installed loader's kind with a
table written in the suite, and runs the installed validator as a real process (`validate.py arch`) over
every present state: exit 0 only for valid. `ready-refusal` drives the ready transition
(`check_ready`) and all seven station decisions under the policy, then again under an accepted record
naming the bytes present: valid and optional absence proceed, everything else refuses with the kind's
named code, and under an accepted record absence is required absence.
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

## 2026-09-23 review: four fixes, each test first

A fresh review of 20221fa..60d5018 found no reachable production defect but four weaknesses, each
reproduced by its own script. Each got a row first, red by a failed assertion over 60d5018's modules,
then the fix, then two registered mutations of that row (the driver's baseline run is the unmutated
control). One commit per item: 7c70d53, 759d9a8, 7633020, 879532f.

**Recorded red at 60d5018.** `red.py 60d5018` runs the current suite with its ROOT pointed at an export of
60d5018's whole `.veldo`. One fixture line reaches the snapshot's single structural validator instance,
which 60d5018 did not have (it re-executed arch.py at every call); for 60d5018 it is replaced by a line
that pins one instance on 60d5018's validate_checks so the injected writer runs, and the record names it.
Result in `red-60d5018.json`: the four new rows fail by assertion with every region completing (no `ran/`
row red), and so do `substitution` and `observations`, whose expected identity now includes validate.py.
The observations show each defect: the store-only Gate passed a required malformed contract; the public
entry saw 0 of 7 judgements; the same Gate passed after arch.py changed on disk and recorded the new
file's digest; the Gate passed validated unaccepted bytes and refused validated accepted ones.

**Item 2, a Gate with no workspace never passes.** Row `architecture/store-only-refuses`: no record, a
policy that requires the contract and a malformed file only a workspace Gate can see; the store-only Gate
refuses `missing_evidence:architecture/workspace` at every station, the workspace Gate refuses
`parse_failure`. Suite 60_0052's two Gates (its main one and the fresh reader process) are given the
workspace they read; it stays at 80 of 80 and `--finding 52` at 47 of 47. Mutations
`architecture-store-only-passes` (reintroduced: only a record makes it refuse) and
`architecture-store-only-reads-cwd` (a missing workspace becomes the process directory).

**Item 5, the public seam.** Row `architecture/public-seam`: an installed copy whose validate.py wraps its
public `entry_contract` with a counter; a Gate loaded from it proceeds at all seven stations and every
judgement went through that name. Mutations `architecture-private-seam` (reintroduced: validate.py's
private validate_checks instance) and `architecture-validate-checks-direct` (validate_checks.py loaded
around validate.py).

**Item 1, the identity is what ran.** Row `architecture/identity-is-what-ran`: a Gate judges an accepted,
structurally invalid contract; the installed contract_loader.py and arch.py are then replaced on disk
(other loader bytes, and a validator that passes everything). The same Gate keeps refusing with the code
it loaded and keeps recording the digests of the bytes loaded, for all five files; a Gate built after the
change proceeds and records the new digests, which shows the change is real. Mutations
`architecture-identity-read-at-decision` (reintroduced: digests read from disk at each decision),
`architecture-validator-reexecuted-per-call` (reintroduced: arch.py executed from disk at every call) and
`architecture-snapshot-per-decision`.

**Item 3, the digest of the bytes validated.** Row `architecture/validated-is-digested`: a writer lands
while the contract is being validated. Validated unaccepted bytes (version 2) are refused and recorded by
their own digest although the file then holds the accepted bytes; validated accepted bytes (version 1)
proceed although the file then changed. Mutations `architecture-digest-second-read` (reintroduced: the
Gate digests the file again) and `architecture-loader-digest-second-read` (the loader reports the digest
of a second read after validation). VELDO-0016's own loader rows and in-suite mutation anchors are
unchanged (suite 29 at 325 of 325).

## Open items

- **(a) No writer for `architecture:<repository>` exists yet.** Nothing on main writes the accepted
  record; the suite writes the plain entity through the real store. Until a writer exists, every real
  repository has no record, so whether its contract is required still comes from the workspace's own
  policy file, which the workspace controls. R50 (a candidate cannot weaken the enforcement that
  authorizes it) is therefore NOT met in production until the writer exists; the enforcement against a
  record is built and proven here, the record's production source is not.
- **(b) The record format needs a written schema.** The Gate reads `{state: accepted, digest: sha256:...}`
  and refuses anything else by name, but the format is defined only by this reader. It must be defined by
  a written schema that the future writer is checked against, so the writer and this reader are not
  matched only to each other.
- **(c) The loader registry row for VELDO-0016.** `policy_contract.LOADER_ADAPTERS` is outside this
  footprint and suite 29 pins its 17 rows, so `validate_checks.entry_contract` (reached through
  validate.py) has no row of its own and suite 29's loader matrix does not drive it; this suite drives it
  instead. The registry scan stays exact because the loader call lives in `validate_checks.py`, a module
  the registry covers, and `control_eligibility.py` calls no loader name. A row for the new entry is owed
  to VELDO-0016's registry.

- **(d) The loader's is_file/open race (VELDO-0016, predates this item).** The loader asks whether the
  path is a regular file and then opens it, as two steps; something that replaces the file between them
  (a FIFO, a symlink to elsewhere) is opened as it is then. A FIFO swapped in there would block the open.
  The bytes parsed are still the bytes digested and compared, so no unaccepted contract passes through
  it; the missing piece is a single open that refuses anything but a regular file (open, then fstat the
  open descriptor). Racing inputs are Release 2 qualification; this belongs to VELDO-0016's loader.

## 2026-09-23 second review: the snapshot in memory, and text that is not UTF-8

A fresh review of 07c7557..8798a78 found fixes 1, 2 and 5 sound and one blocker in the snapshot: the
private copy on disk could be swapped by another process of the same account between the snapshot's write
and its load (probe `r4c_inotify_tmp.py` did it over the real /tmp with inotify), so the Gate ran code whose
digest it had not recorded. Each fix below got a row first, red by a failed assertion over 8798a78's
modules, then the fix, then two registered mutations (the driver's baseline run is the unmutated control).

**The snapshot runs from memory** (ec80409). Row `architecture/snapshot-in-memory`: a same-account writer
acts at the one moment a copy on disk is exposed, just before any engine module is loaded from a path
outside the installed engine, and replaces the arch.py beside it with one that passes everything. At
8798a78 it swapped the private arch.py 11 times, the Gate passed a structurally invalid accepted contract
and recorded the installed validator's digest. Now no engine module of the validator is loaded from any
path on disk, nothing is written, the contract is refused by name and the recorded digests are the
installed bytes'. Mutations `architecture-snapshot-private-copy` (reintroduced) and
`architecture-siblings-from-disk` (the top module from memory, its siblings from disk).

**Text that is not UTF-8** (3901ed5). Row `architecture/not-text-refused`: an accepted contract whose bytes
end in a comment that is not UTF-8 is refused `invalid_input:architecture/parse_failure` with the digest of
those bytes recorded; at 8798a78 the decode error escaped the loader and every station said
`unavailable_service:architecture_validator`. The decode is now explicit UTF-8 inside the named refusal.
Mutations `architecture-decode-outside-refusal` (reintroduced) and `architecture-decode-lossy` (a
replacing decode parses the rest).

## Narrowest seams, stated

- **The accepted architecture record.** See open items (a) and (b).
- **The loader registry.** See open item (c).
- Not isolated: the executor's `_decide_calls` registration is always preceded by its station decision,
  which asks the same predicate first, so its driver shows the refusal of that earlier decision. Under
  `architecture-review-skipped` the executor's review still refuses at its provider-request boundary;
  the dispatcher's direct review is the launch the declared falsifier turns red.
- Release 2, not added: concurrent architecture inputs and racing revision qualification. Running the
  suite as root cannot deny a read, so `state-kinds` would red there rather than pass without the denial.

## Cost and verification

Suite 60_veldo_0053 runs in about 1.2 s (`observations.json`, `suite_seconds`), including seven
installed-validator processes run in sequence; a validator snapshot costs about 23 ms once per Gate and a
judgement about 0.7 ms. `--finding 53` drives 22 mutations in 68 s here (44 suite runs), about 9 s of wall
time in the gate's 8-worker mutation stage. Targeted checks on this branch after the review fixes:
`python3 -B scripts/selftest.py --suite 60_veldo_0053_architecture` (21 rows, 47 assertions with the
shared preamble, 0 failed), `python3 -B scripts/check_teeth_mutations.py --finding 53` (22 rejected, no
`ran/` row red), `--finding 52` (47 rejected, suite 60_0052 at 80 of 80), the whole
`python3 -B scripts/selftest.py` (5850 passed, 0 failed; not the gate), `python3 .veldo/validate.py all`
(exit 0), `bash scripts/check_generated.sh` and `bash scripts/check_template_sync.sh` (pass). The full
gate is run by the lead.

`red.py 60d5018` regenerates `red-60d5018.json`. `drive.py` regenerates `observations.json` from one run of the suite.
