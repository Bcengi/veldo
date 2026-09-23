# VELDO-0037 proof

Implementation: counter-based specification alias allocation, source-tuple idempotency, versioned
edits guarded by expected version and content digest, and exact publication of accepted document
bytes with an independent reader. Specification remains **ready**. This bundle is implementation
evidence from a builder worktree. It is not independent engineering review, owner approval, service
activation or a gate result: the full `bash scripts/verify.sh` is run by the lead, serially, and no
`manifest.json` binding a verified commit is written here for that reason.

Targeted verification actually run on this branch:

```text
python3 -B scripts/selftest.py --suite 59_veldo_0037_aliases
  59_veldo_0037_aliases   35 passed   4.22s
  selftest (PARTIAL, 1 of 72 suites): 61 passed, 0 failed
python3 -B scripts/check_teeth_mutations.py --finding 37
  {"mutations_rejected": 44, "green_suites": {"59_veldo_0037_aliases.py": 61}}
python3 .veldo/validate.py all        exit 0
bash scripts/check_generated.sh       generated: pass
python3 -B proof/VELDO-0037/red_at_f84f2d2.py
  the recorded-numbers row and row 14, and only they, fail against f84f2d2's modules
python3 -B proof/VELDO-0037/red_at_9930b32.py   (recorded before the recorded-numbers fix; see below)
  the two third-check rows, and only they, failed against 9930b32's modules
python3 -B proof/VELDO-0037/red_at_9421af6.py   (recorded before the third check; see below)
  the five second-review rows (and the renamed-code row) failed against 9421af6's modules
python3 -B proof/VELDO-0037/red_at_adfb89a.py   (recorded before the second review; see below)
  the eight review-defect rows, and only they, failed against adfb89a's modules
```

## Components

`control_alias.py` registers four commands on one store connection, exactly as VELDO-0035's read
sets do: `enable_artifact_kind`, `allocate_document`, `edit_document`, `record_publication`.
`control_store.execute` is still the only writer and every transition runs inside its
`BEGIN IMMEDIATE` on that connection. Entities, all namespaced by repository UUID:

| Entity | Kind | Holds |
|---|---|---|
| `artifact-kind/<repo>/<kind>` | `artifact_kind` | prefix, width, path template and the counter `next` |
| `alias/<repo>/<alias>` | `alias_reservation` | the reserved alias and number, never released |
| `alias-source/<repo>/<key>` | `alias_source` | source tuple, role, alias, version, digest |
| `document/<repo>/<alias>` | `accepted_document` | current accepted version and digest |
| `document/<repo>/<alias>@<n>` | `document_version` | immutable content (UTF-8 text), digest, prior digest |
| `publication/<repo>/<alias>@<n>` | `publication_obligation` | pending or published, observed digest |

The source key is the digest of (repository, source system, source id, source revision, intended
artifact role). A role is `<kind>` or `<kind>/<label>`, so one source can produce several
specifications and other artifacts. `control_document.py` holds the publisher (exclusive creation
of version 1 by hard link of a verified, fsynced temporary file; atomic rename for later versions,
only over the prior accepted bytes) and `read_published`, which reads the newest version recorded
published and compares the complete file with the accepted records.

Authority startup calls `control_alias.attach(store, conn, domain_uuid, repositories)`, where
`repositories` maps each enrolled repository UUID to its accepted Git repository. A kind is enabled
once per repository by naming a VELDO-0035 `accepted_revision` entity; the enabling transition
reads that commit's tree and history (`accepted_maximum`, C9) and derives the first number, or
verifies a caller's first number is above every historical one. Allocation never reads any tree
again. A `Publisher` is bound to the repository its checkout's root commits identify (superseded: since the
second review it is bound by the checkout's enrollment binding; see the last section). Both modules are installed by
`_FILES` in both copies of `init_scaffold.py`; they are runtime assets, not validator imports, so
they are not `REQUIRED_SUBSTRATE`. Canonical `engine/.veldo` files and installed `.veldo` copies are
byte-identical. The store, its schema, `control_snapshot.py`, `claim.py` and `git_process.py` are
consumed unchanged. No dependency is missing on main, so no seam was added outside the footprint.
(Superseded by the second review: entity ownership moved into `control_store.py` and accepted
revisions gained their own command in `control_readset.py`, both added to the footprint.)

## Criteria and observed rows

Suite `scripts/suites/59_veldo_0037_aliases.py`, 35 rows (19 below, 16 in the review sections). It uses a real SQLite store, a real Git
origin and three clones (two requester workspaces and the authority's publication checkout), real
Ed25519 journal signatures through `ssh-keygen`, separate allocation processes and separate
read-only reader processes. `observations.json` retains every row and the suite's observations.

| Criterion | Rows | What actually ran |
|---|---|---|
| AC1 | `aliases/stale-checkouts`; `aliases/same-source-reuse`; `aliases/distinct-source`; `aliases/stale-read-refused`; `aliases/no-recycling`; `aliases/per-repository`; `aliases/invalid-unit-id`; `aliases/accepted-floor` | Kinds enabled from the accepted commit (specification 4, plan 3, decision 5). Three independent processes, from two clones whose checkout maximum stays VELDO-0003, receive VELDO-0004, 0005, 0006. An identical request from another process and clone reuses VELDO-0004 with no journal record. Varying system, id, revision, role label, and role kind (plan, decision) each allocates a new alias. A command authored from a counter read that another allocation then moved refuses `stale_version` with every domain table unchanged. Publishing and deleting a file and re-enabling the kind at 4 recycle nothing (the next allocation is VELDO-0013; reserved numbers 4-13, each once). Counters are per repository; an unenrolled repository refuses `wrong_repository`. Prefixes `VEL DO`, `VELDO/X`, `../VELDO` and an edit or publication naming `VELDO-0004/../x` refuse `invalid_unit_id` with exactly `claim.unit_id_problem`'s text, before any entity or file is written. |
| AC2 | `documents/edit-current`; `documents/identical-reuse`; `documents/changed-content-conflict`; `documents/stale-overwrite` | Against a real accepted and published VELDO-0004: a current edit creates version 2, keeps version 1's bytes, leaves v2 pending and the reader still on v1. The identical edit repeated reuses version 2 with no journal record. The same source tuple with other bytes, for an edit and for an allocation, refuses `source_content_conflict` with tables unchanged. After v3 re-accepts v1's bytes, four overwrite attempts refuse with tables unchanged and versions 1-3 intact: stale version with current digest (`stale_version`), old version (`stale_version`), current version with the wrong digest (`stale_document`), unknown digest (`stale_document`). |
| AC3 | `publication/accepted-documents`; `publication/commit-together`; `publication/exclusive-create`; `publication/replace-declared-version`; `publication/replace-guard`; `publication/tampered-refused`; `aliases/observations` | One document per enabled kind (VELDO-0004 with CRLF, non-ASCII and no final newline; PLAN-0003; VELDO-DEC-0005) is published; a separate process compares alias, version, digest, source tuple, role, path and the complete bytes with expected values computed independently with `hashlib`. VELDO-0004's allocation is one signed, verified journal record containing exactly the counter, reservation, mapping, head, version 1 and obligation. A pre-existing file at a new declared path refuses `publication_conflict` untouched. Versions 2 and 3 replace the file in order; publishing a version whose predecessor is unpublished refuses `publication_order`; an externally edited file is never overwritten. Edited bytes refuse `document_mismatch`, a removed file `missing_publication`. Counts, taxonomy categories, command/seq/record-digest trace joins, pending obligations and the absence of document text in observations are checked. |

## Driven negative controls

Registered in `scripts/check_teeth_mutations.py` as finding 37 and therefore in
`check_gate_mutations.py`'s stage. `mutations.json` (from `drive.py`) records, per case, the
baseline, a byte-identical no-op copy and the mutant: target observations, every red row, module
digests, and the suite's own observations under the mutant. Each named row failed its assertion;
no case raised, hung or lost rows. Exact edits are the adjacent `.diff` files.

| Criterion | Mutation | What the mutant did | Named row turned red |
|---|---|---|---|
| AC1 declared falsifier | `alias-checkout-maximum` | number = requester checkout maximum + 1; the second and third independent requests collide on VELDO-0004 and refuse `stale_version` | `aliases/stale-checkouts` |
| AC1 second | `alias-counter-not-advanced` | the counter is written back unchanged; the next request hits the reserved alias | `aliases/stale-checkouts` |
| AC2 declared falsifier | `document-ignore-digest` | the expected digest is ignored; the current-version wrong-digest edit commits | `documents/stale-overwrite` |
| AC2 second | `document-current-version` | the service declares the head's current version instead of the caller's; the stale edit carrying v1's digest commits over v3 | `documents/stale-overwrite` |
| AC3 declared falsifier | `publication-altered-bytes` | altered bytes are written under the accepted digest with the temporary-file check removed; since the review fixes the publisher's re-read of the declared path refuses `publication_mismatch` (and the recording transition would too), so the reader sees no published version | `publication/accepted-documents` |
| AC3 second | `publication-normalized-newlines` | CRLF is normalized on write; the publisher's own comparison refuses | `publication/accepted-documents` |
| extra | `reader-trusts-record` | the reader trusts the recorded digest instead of hashing the file | `publication/tampered-refused` |
| extra | `alias-skip-unit-id` | the enable-time `claim.unit_id_problem` call is removed | `aliases/invalid-unit-id` |

## Scope

Release 2 items were not added: no concurrency or restart matrix, no recovery of a publication
interrupted between rename and record, no publisher exclusion across processes, no fencing, no
remote acknowledgement. `allocate` rereads the counter only when a `stale_version` refusal shows the
counter moved since its read (bounded, then `allocation_contention`); a refusal for any other reason
is returned as is. Authentication and business authorization of requesters stay with the calling
service; the principal handed in is recorded. No policy, specification status or other
specification changed. The mutation-registry footprint exception is in the specification's
History and machine-readable footprint.

## Gate cost and evidence size

`timing.json` (rewritten after the review fixes): the suite runs in 2.77 s in process (2.1 to
2.3 s under `selftest.py --suite`); the gate runs it twice (unit and first-use integration). Most of
the growth is the eight review rows, each with its own store (FULL synchronous commits), Git
repositories and real signatures. The 24 mutation cases take 158.6 s serial for baseline, no-op and
mutant runs (about 2.2 s per suite run); the gate shares baseline and no-op controls per suite and
module (2 groups) and runs 8 workers in parallel, so its added wall time is about a third of that.
Conservative added workload: about **40 s** (suite twice about 5.5 s, mutation stage about 30 s).
**Note for the lead:** `check_gate_mutations.py` has a combined 120 s stage budget, now across 140
registered cases (both drivers), and finding 37 alone is now 24 of them. Proof is readable JSON,
Markdown, Python, a plain-text re-run log and small diffs, with no keys, signatures, encoded blobs,
bytecode or gate logs.

## Independent review fixes (2026-09-23)

An independent reviewer reproduced six defects in adfb89a with standalone scripts, and suspected
two more that matter because the Mac is a Release 1 worker host. Each was fixed test first, one
commit per defect: a new suite row, recorded RED against adfb89a by failing its assertion, then the
fix, then two registered mutations for finding 37 that turn that row red again. Every row owns a
separate store, authority and accepted repositories, so it does not disturb the rows above.
`red-at-adfb89a.json` (from `red_at_adfb89a.py`) runs the final suite against adfb89a's
`control_alias.py` and `control_document.py`: the suite completes, the 19 original rows pass and
exactly these eight fail.

| # | Defect | Row | At adfb89a (recorded RED) | Fix | Mutations (both red the row) |
|---|---|---|---|---|---|
| 1 | A symlinked parent was followed | `publication/no-symlink-escape` | bytes written to the symlink target outside the checkout and recorded; the reader accepted a symlinked parent and a symlinked file | every declared path is walked from the checkout root through directory descriptors opened with `O_NOFOLLOW`, for writing, re-reading and reading: `unsafe_path` | `publication-follow-parent-symlink`, `reader-follows-links` |
| 2 | Two kinds' templates could declare one path | `aliases/one-path-per-kind` | a same-path, a directory-of and a slug-meets-number template were all accepted | enabling walks the new template against every kind of the repository and refuses a shared path or a directory of the other's path: `invalid_registration` | `alias-overlap-unchecked`, `alias-overlap-ignores-directories` |
| 3 | The caller's first number was trusted | `aliases/historical-floor` | an unaccepted revision and `first: 1` were accepted and VELDO-0001 issued again | enabling names an `accepted_revision` entity with its version declared; the transition reads that commit's tree and history (a deleted VELDO-0002 still counts) and derives the first number, or refuses `below_accepted_history` | `alias-trusts-first-number`, `alias-floor-ignores-history` |
| 4 | A publication was recorded on a caller's digest | `publication/recorded-only-by-publisher` | recorded published with no file, after which the publisher refused the version forever | the recording transition reads the declared path through the bound publisher inside its own transaction: no publisher `missing_authority`, no file `missing_publication`, other bytes `publication_mismatch` | `record-trusts-supplied-digest`, `record-missing-file-accepted` |
| 5 | Generic store commands rewrote alias records | `aliases/generic-writes-refused` | the counter was rewound to 1, a reservation retired and a version overwritten; the next allocation failed | `attach` guards every command already registered on the connection so it cannot write an owned entity (by id prefix, or its kind before or after): `allocation_owned`; other entities are unaffected | `alias-generic-commands-unguarded`, `alias-guard-by-new-kind-only` |
| 6 | Publisher and reader were not bound to a repository | `publication/bound-to-repository` | another repository's document was written into this checkout and read back as its own; a plain directory was accepted as a publisher root | a repository's identity is its root commits (control_enrollment's rule); a Publisher binds to the one repository its checkout carries, the reader checks the checkout against the kind's recorded roots: `wrong_repository` | `publisher-any-repository`, `reader-any-checkout` |
| 7 | Case-only differences were accepted | `aliases/case-insensitive-names` | `VELDO` and `veldo`, and `Docs/` and `docs/`, were both accepted; a non-ASCII template too | prefixes and the overlap walk are case-folded, a historical number counts whatever its case, templates are ASCII | `alias-prefix-case-sensitive`, `alias-paths-case-sensitive` (a hand-driven third, a case-sensitive history pattern, also reds the row) |
| 8 | Templates could reach `.git/` or `.veldo/` | `aliases/reserved-directories` | `.git/`, `.veldo/claims/`, a nested `.GIT/`, `.{slug}/` and `.Veldo/` were all accepted | every template component is walked against `.git` and `.veldo` case-folded: `reserved_path`; `.github/` stays allowed | `alias-reserved-unchecked`, `alias-reserved-literal-only` |

Consequences for callers. `attach` now takes a mapping of repository UUID to accepted repository
and refuses two repositories with the same root commits. `enable_kind` requires `revision_id`;
`first` is optional. A `Publisher` root must be the top level of a Git checkout of an enrolled
repository, and one checkout publishes per repository. The suite's decision kind moved from
`.veldo/decisions/` to `decisions/`, because rule 8 now refuses every template under `.veldo/`.

Known limits, stated rather than fixed here. The generic-command guard wraps what is registered
when `attach` runs; `control_readset.ReadSets.enable` wraps `store.COMMAND_REGISTRY` directly, so a
read set enabled for a generic command after `attach` replaces its registration and drops the
guard. Attach the allocation authority last; the lasting fix is an ownership rule in
`control_store`, outside this footprint. (Fixed by the second review: that ownership rule now exists
and the guard is gone; see the last section.) The template overlap walk over-approximates (it ignores a
slug's hyphen placement and a number's leading zeros), so it can refuse a pair the counter would
never actually collide; it never accepts a pair that can. `claim.py` keys its ledger by the id's
own case, so `VELDO-0001` and `veldo-0001` would share one record on macOS; rule 7 keeps the alias
domain from minting such a pair, and `claim.py` itself is unchanged.

### Re-running the reviewer's scripts

All nine of the reviewer's scripts (`r1`-`r7`, `s1`, `s2`) were re-run against the final code
(0edc694 production modules) and **none prints BUG**; none raises. `review-rerun.txt` is the output
and `review-rerun.diff` is every change made to the scripts. Their shared harness targets the old
API, so the adapted copies (a) load this worktree's modules, (b) attach with a mapping to an accepted
Git repository, seed an `accepted_revision` and clone the publisher's checkout from it, (c) pass
`revision_id` when enabling, (d) catch `control_document`'s own `Refused` class as the suite does,
(e) in `r2` and `s2` take the now-refused second kind's allocation as a refusal instead of an
uncaught exception, (f) in `r3` bind the store to the reviewer's history repository and enable with a
derived first number after the refused `first: 1`, and (g) in `r7` use two distinct accepted
repositories. Every BUG condition is byte-identical to the reviewer's.

| Script | Result on the final code |
|---|---|
| `r1_symlink_parent` | publish `unsafe_path`, nothing outside the root, reader `missing_publication` |
| `r2_path_collision` | second kind refused `invalid_registration`; only one alias holds `docs/0001.md` |
| `r3_first_below_history` | `first: 1` refused `below_accepted_history`; derived allocation VELDO-0002 |
| `r4_record_without_bytes` | record refused `missing_publication`, obligation still pending; the publisher then publishes |
| `r5_exact_bytes` | nine awkward byte cases exact (mode 0600 under umask 077); two non-UTF-8 inputs refused `invalid_input` |
| `r6_generic_upsert` | `upsert_entity` refused `allocation_owned`; the counter stays at 4 and the next allocation succeeds |
| `r7_cross_repository` | publishing `other` refused `wrong_repository`; this repository's own document publishes |
| `s1_parallel` | 24 processes over 12 sources: 12 aliases, no errors, no alias given twice; VELDO-0013 after reopening |
| `s2_case_prefix` | `veldo` refused `invalid_registration`; a template into `.git` refused |

## Second independent review fixes (2026-09-23)

A second independent check reproduced five more defects in 9421af6 with standalone scripts. Each
was fixed test first, one commit per defect: a new suite row (rows 9 to 13 of the suite's defect
section), recorded RED against 9421af6 by failing its assertion, then the fix, then two registered
finding-37 mutations that turn that row red again. Defects 4 and 5 have one root cause and it was
fixed once, in the store; the defect 5 commit adds what that fix still left open for VELDO-0035's
own kind.

**RED record.** `red-at-9421af6.json` (from `red_at_9421af6.py`) runs the final suite with the four
modules the fixes changed (`control_alias.py`, `control_document.py`, `control_store.py`,
`control_readset.py`) taken from 9421af6 and every other module from this tree. The suite completes
and exactly six rows fail: the five new rows, and `aliases/generic-writes-refused`, whose four cases
9421af6 does refuse, under the old code name `allocation_owned` (the row now expects the store's
`entity_owned`). 9421af6 has no `accept_revision` and takes no enrollment arguments, so the harness
appends to the old modules exactly the entry points the suite calls and nothing that checks
anything: `attach_revisions(...).accept(...)` writes the accepted revision with the generic
`upsert_entity`, as 9421af6's callers did, and `Publisher` and `read_published` accept and drop the
enrollment arguments. The shims are recorded verbatim in the JSON.

| # | Defect | Row | At 9421af6 (recorded RED) | Fix | Mutations (both red the row) |
|---|---|---|---|---|---|
| 1 | Enabling could name an earlier accepted revision, and the generic `upsert_entity` wrote accepted revisions freely | `aliases/floor-from-every-accepted-revision` | a generic write of a new accepted revision at the pre-spec commit and a generic rewrite of the current one both committed, the current one moved back to that commit, `first: 1` naming it was accepted, and VELDO-0001 was issued again although the accepted HEAD holds `specs/VELDO-0001-held.md` | the enabling transition takes its floor over EVERY accepted revision of the repository, read inside its transaction (the named one only proves the request stands on one). Accepted revisions are written only by the new `accept_revision` (`control_readset.Revisions`, VELDO-0035's module), which checks the commit, documents and statuses exactly as `inputs()` checks them when consumed and refuses `revision_regression` when a revision id would move to a commit that does not descend from its current one. `attach_revisions` and `control_alias.attach` both declare `accepted_revision` store-owned by it | `alias-floor-named-revision-only`, `revision-regression-allowed` |
| 2 | The history walk's path filter was case-sensitive, and the slug grammar dropped files that hold a number | `aliases/floor-counts-every-carrier` | floors 1, 1, 1 and 2 where `Specs/VELDO-0005-b.md`, `specs/VELDO-0007-foo_bar.md`, `specs/VELDO-0008.md` and `Decisions/0009_B.YAML` hold 5, 7, 8 and 9 | a file counts when its name CARRIES the kind's number: the template's leading directories matched case-insensitively, then the component holding `{alias}` or `{number}`, whatever surrounds the number there or lies below it. The history walk is narrowed with an `:(icase)` pathspec; `ls-tree` has no icase magic, so it lists the whole tree and the pattern filters it. `XVELDO-0090`, `other/VELDO-0080` and `notes-0070` still count nothing | `alias-floor-pathspec-case-sensitive`, `alias-floor-slug-grammar` |
| 3 | Two repositories sharing a root commit confused their checkouts | `publication/bound-by-enrollment` | an unenrolled clone of B (A plus a merged unrelated history) checked out before the merge bound as A; the edited binding was never read (that clone bound as B from its root commits), and the later binds collided with those two | a checkout is bound by the VELDO-0029 binding it carries, never by root commits: `control_document.enrolled_repository` reads it with `control_enrollment`, requires `verify_binding` to pass (signature, this clone's UUID, the root commits the checkout has now, host, domain) and the binding to name the store the service has open, and answers its `repository_uuid`. Unenrolled, moved after enrollment, an edited binding and a binding for another store all refuse `wrong_repository`; the same pre-merge clone enrolled as B binds as B and refuses A's document; the reader checks the checkout the same way | `publisher-infers-root-commits`, `binding-signature-unchecked` |
| 4 | The generic-write guard lived on the connection `attach` ran on | `aliases/owned-on-every-connection` | from a second connection (another copy of the store module, nothing registered) and from one opened before `attach`: the counter was rewound to 1, VELDO-0001@1 rewritten and then relabelled, a reservation retired | ownership moved into the store (below) | `store-owners-only-where-registered`, `store-owners-unchecked` |
| 5 | `ReadSets.enable` after `attach` re-registered from the module-global registry and dropped the guard | `aliases/owned-whatever-registration-order` | with the read set enabled after `attach`, a snapshot-bound `upsert_entity` rewound the counter to 1; in either order a `control_snapshot` was forged by a generic write from a plain connection | the same store rule; and `control_readset.attach` declares `control_snapshot` store-owned by `accept_snapshot` | `store-owners-skip-registered-transitions`, `readset-snapshots-undeclared` |

**The root cause, fixed once in the store.** `control_store.declare_owners(conn, owner, kinds,
prefixes)` persists, for each owned entity kind and each owned entity id prefix, the commands
allowed to write it, in the store's own `entity_owners` table. `control_store.execute` reads the
table inside every command's `BEGIN IMMEDIATE` and refuses `entity_owned` when a command writes an
entity that any matching declaration does not allow it to write, matched by the entity's kind
after the write, its kind before it, and every declared prefix of its id. It therefore binds every
connection to the file, whatever was registered where and in what order, and the per-connection
`_guard_generic` wrapper is gone. A declaration is immutable: repeating it is a no-op; a different
one for a declared kind or prefix, or a first one for a kind or prefix that entities already
occupy (they were written while nobody owned them), refuses `ownership_conflict`. The declarations
made: `control_alias.attach` owns its six kinds and five id prefixes, each with only the commands
that write it (the counter: `enable_artifact_kind` and `allocate_document`; a reservation:
`allocate_document`; mapping, head and versions: allocate and edit; obligations: allocate, edit and
`record_publication`), plus `accepted_revision` for `accept_revision`; `attach_revisions` owns
`accepted_revision`; `control_readset.attach` owns `control_snapshot` for `accept_snapshot`. The
table is created by the first declaration rather than in `_DDL`, so a store nobody declared into
carries exactly the eight `DOMAIN_TABLES` that VELDO-0023's AC1 row pins, and no owner rule. The
store's command registry, its domain tables and its behavior for undeclared entities are unchanged.

**Consequences for callers.** Accepted revisions are written with
`control_readset.attach_revisions(store, conn, domain_uuid, repositories).accept(revision_id,
repository_uuid, commit, principal, documents, statuses, **signing)`; a generic write of an
accepted revision, a snapshot or any alias entity refuses `entity_owned` on every connection of a
store they are declared in. `Publisher(service, root, verify, host_identity)` and
`read_published(store, conn, repository, alias, root, verify, host_identity, domain_uuid)` take the
enrollment verifier, and every checkout that publishes or is read must be enrolled
(`control_enrollment.enroll`) against the service's store; `control_enrollment.py` is therefore now
installed by `_FILES` in both copies of `init_scaffold.py`. `attach` no longer refuses two
repositories that share root commits, since nothing binds by them. The refusal `allocation_owned`
is now the store's `entity_owned` (taxonomy `missing_authority`); `ownership_conflict` is
`invalid_input`. A kind record gains `floor_commits`, the accepted commits its floor came from.

**Footprint and regressions.** `control_store.py` (VELDO-0023) and `control_readset.py`
(VELDO-0035) were added to the specification's footprint in all three copies, with a History line.
Every control-store suite was run after the change and is green: `36_veldo_0023_journal`,
`37_veldo_0024_replica`, `38_veldo_0025_membership`, `39_veldo_0026_revocation`,
`46_veldo_0029_enrollment`, `56_veldo_0027_signing`, `58_veldo_0035_snapshots`,
`58_veldo_0036_reservations` (there is no 0031 suite under `58_*`); so are the suites that read
`init_scaffold._FILES` (`01`, `03`, `08`, `11`, `12`, `13`, `14`, `26`).
`check_teeth_mutations.py --finding 35` still rejects all 12 of VELDO-0035's mutants, whose anchors
in `control_store.py` and `control_readset.py` are unchanged.

Known limits, stated rather than fixed here. The ownership table is store state outside the
journal, like the publication cursor, so a store rebuilt from its journal (recovery is Release 2)
carries no declarations; the owners' next `attach` then finds their namespaces occupied and refuses
`ownership_conflict`, which fails closed but means that recovery work has to restore the
declarations with the entities. Ownership is by command name: two services registering commands of
the same name are trusted code, and `attach` refuses a second allocation authority on one
connection (superseded by the third check: ownership is now bound to the owning module's file and
digest, see the last section). The carrier pattern over-counts on purpose (`specs/VELDO-0010.txt` holds 10), since a
skipped number costs nothing and a reissued one is a second document under one identity.
`red_at_adfb89a.py` was recorded against the suite as it stood at 9421af6; the final suite calls the
new entry points, so that record stands as history and is not re-runnable unchanged.

### Re-running both reviewers' scripts

All nineteen scripts, the second reviewer's ten (`t1`-`t8`, `t1b`, `t6b`) and the first
reviewer's nine, were re-run against the final production modules: **none prints BUG, none
raises, all exit 0**, and `t1` rows A and C give their expected floors, 5 and 8 (B 9, B2 9, D 6;
`t1b` 9; `t2` over the real repository 132 with no skipped name). `review2-rerun.txt` is the output
and `review2-rerun.diff` every change made to the scripts, on top of the first review's recorded
adaptations (`review-rerun.diff`, re-applied). The new adaptations: (a) the harnesses load this
worktree's modules; (b) accepted revisions are written with `accept_revision`, except that `t3`
keeps the reviewer's generic write (refused `entity_owned`) and then writes the earlier revision the
sanctioned way so the enable naming it still runs; (c) publishing and reading checkouts are enrolled
and handed the verifier, except that `t4` keeps the reviewer's unenrolled pre-merge clone and then
enrolls that same clone as B under the same BUG condition; (d) the harness catches the read set
module's own `Refused`. Every BUG condition is byte-identical to the reviewer's.

| Script | Result on the final code |
|---|---|
| `t1_floor` | A 5, B 9, B2 9, C 8, D 6: every expected floor |
| `t3_old_revision` | `first: 1` refused `below_accepted_history`; the generic accepted-revision write refused `entity_owned`; enabling on the earlier revision allocates VELDO-0002 |
| `t4_shared_root` | the pre-merge clone of B binds as nothing (`wrong_repository`); enrolled as B it binds as B and publishing A's document there refuses `wrong_repository`, no file |
| `t5_other_connection` | allocation connection and second connection all refuse `entity_owned`; counter 4 stays 4, VELDO-0001@1 unchanged |
| `t6_readset_after`, `t6b_order` | snapshot accepted, snapshot-bound rewind refused `entity_owned`, counter stays 4, in both orders |
| `t2`, `t1b`, `t7`, `t8`, first review `r1`-`r7`, `s1`, `s2` | as before these fixes (see `review2-rerun.txt`); `r6` now refuses `entity_owned` |

### Gate cost after the second review

`timing.json` (rewritten by `drive.py`): the suite runs in 4.5 s in process under the proof
driver and 3.4 to 3.6 s under `selftest.py --suite` (32 rows, 58 assertions with the shared
preamble); the gate runs it twice. The five new rows cost about 1 s: each owns a store, real Git
repositories, real journal and enrollment signatures, and the enrollment verifier is one
`ssh-keygen -Y verify` per bind or read. The 34 finding-37 cases take 492.7 s serial for baseline,
no-op and mutant runs; `check_teeth_mutations.py --finding 37` took 3 min 57 s serial here, and
`check_gate_mutations.py` shares baselines and runs 8 workers, so its added wall time is roughly a
third of the serial figure. **Note for the lead, repeated:** finding 37 is now 34 of the registered
cases in `check_gate_mutations.py`'s combined 120 s stage budget, up from 24.

## Third independent check fixes (2026-09-23)

A third independent check reproduced two defects in 9930b32 with standalone scripts (`p1`-`p6`,
`p3b`). Each was fixed test first, one commit per defect: a new suite row (rows 14 and 15 of the
defect section), recorded RED against 9930b32 by failing its assertion, then the fix, then
registered finding-37 mutations that turn that row red again. A third commit closes a hole the
second fix opened (below).

**RED record.** `red-at-9930b32.json` (from `red_at_9930b32.py`) runs the final suite with the three
modules the fixes changed (`control_alias.py`, `control_store.py`, `control_readset.py`) taken from
9930b32 and every other module from this tree. The suite completes and exactly the two new rows
fail. No shims were needed: both rows call only entry points 9930b32 has, and the one new keyword
(`declare_owners(module=...)`) is caught as `TypeError` inside the row and recorded as its value.
Re-run on f84f2d2, it wrote a byte-identical record (the recorded-numbers row changed the suite
afterwards, so it now stands as history too). `red_at_9421af6.py` no longer runs against the
final suite (row 14 registers `Revisions.transition` directly, which its shim does not have), so its
record stands as history, like `red_at_adfb89a.py`'s.

| # | Defect | Row | At 9930b32 (recorded RED) | Fix | Mutations (each reds the row) |
|---|---|---|---|---|---|
| 1 | `accept_revision` accepted a commit the allocation authority's repository does not contain, and every later `enable_artifact_kind` then refused `invalid_input` with nothing able to clear it | `aliases/revision-in-enrolled-repository` | a revision service attached to an unrelated repository, and one attached to a clone holding an unpushed commit, both accepted; the same through `Revisions` registered without attach; every later enabling refused `invalid_input`, so no alias was allocated; the kind enabled beside a raw-SQL revision, and a directly registered `Allocations` reading another path, refused `invalid_input` too (the floor was already poisoned), and the allocation authority's own attach to the clone was accepted | the first attach (`attach_revisions` or `control_alias.attach`) binds each repository UUID of the domain to its accepted repository in the store (`control_store.bind_repositories`, all or none, the `repository_bindings` table); another path refuses `repository_binding_conflict`. `accept_revision`'s transition reads the binding inside its transaction and refuses `unenrolled_commit` when the bound repository does not hold the commit at acceptance time, whatever path its object was built with. The enabling transition refuses `wrong_repository` when its object reads another path than the bound one, reads the bound repository, and takes its floor only over accepted commits that repository holds, so a revision no command could have accepted (the row writes one by raw SQL) cannot poison it. After the clone's commit reaches the bound repository it is accepted and its number (VELDO-0007) raises the floor: the next alias is VELDO-0008 | `revision-any-repository` (reintroduces it), `floor-counts-unheld-revisions`, `enable-reads-unbound-repository`, `repository-binding-unchecked` |
| 2 | Ownership was keyed on the operation NAME a connection registers, so a connection registering its own transition as `enable_artifact_kind` or `accept_revision` passed it | `aliases/owned-by-code-not-name` | transitions this suite registered as `enable_artifact_kind`, `accept_revision` and `accept_snapshot` all committed (the counter rewound to 1, a revision with commit `fff...f` and a snapshot forged), and so did the genuine `Allocations._transition` wrapped around a body from the suite; the declaration held no module; an edited copy of the alias module kept writing | each declaration records the owning module's resolved file and the sha256 of its bytes, which the store reads itself (`declare_owners(..., module=__file__)`). Before an owned command's transition runs, `execute` requires that the registered callable, followed through bound methods and every closure cell, was compiled from exactly that file, and that the file still has that digest; otherwise it refuses `foreign_transition` and runs nothing. A command already bound to other code refuses `ownership_conflict` at declaration. The genuine module attached on another connection still allocates (VELDO-0003); the edited copy is refused until its bytes are restored | `store-owner-by-name` (reintroduces it), `store-owner-ignores-digest`, `store-owner-outer-code-only` |

**The hole the second fix opened, closed in its own commit.** Re-running `p4` showed that a
declaration naming one of the store's own generic commands (`upsert_entity` as the "owner" of a
squatted prefix) would bind that command to a foreign module, so every `upsert_entity` on the
store, for any entity, would refuse `foreign_transition`. A declaration may no longer name any
`COMMAND_REGISTRY` command (`malformed_command`); they are what ownership keeps out. Row 15 asserts
it and the generic write beside it, and `owners-may-name-generic-commands` reds the row.

**What clears a revision recorded before this fix: none needed, because none exists.**
`accept_revision` was introduced on this branch (e3f3f45) and main has none, so a revision it
recorded without the repository check exists only in this branch's test stores. A store holding
accepted revisions written by generic commands before any declaration already refuses both
attaches `ownership_conflict`, and after a declaration such a write is refused `entity_owned`. And
if one exists anyway, it no longer poisons anything: the floor skips a commit the bound repository
does not hold. (Superseded by the recorded-numbers fix, last section: such a revision is now refused
by name at enabling instead of skipped.)

**Found while checking this proof, then fixed (see Recorded numbers, the last section).** That skip did not
tell a revision nobody could have accepted from one `accept_revision` rightly accepted whose commit
the bound repository later lost (a deleted branch and `gc`, or a force push). Builder probe
`q7_lost_commit` accepts a revision on a side commit holding `specs/VELDO-0009-side.md`, deletes the
branch and prunes it, then enables the kind: at f84f2d2 enabling commits with `next = 1` and
`floor_commits` naming only the main commit, so VELDO-0009 can be issued a second time and nothing
fails. At 9930b32 the same probe refused `invalid_input` (`accepted commit must identify an
existing commit`), which failed closed. The brief asked that a revision the floor could not have
accepted never poison it; the fix also dropped revisions it did accept. The lead chose the design.

**Stated limits, not claims** (also in the specification's Notes and the store's docstring).
Enforcement lives in `control_store.execute` under a same-account threat model, so raw SQL on the
store file, a store module copy from before the rule (`p6` still prints its `BUG(limit)` line), and
deleting the `entity_owners` table (`p4a`'s last case) all write owned entities; so does code that
deliberately compiles a function under the declared file name, or patches the owning module's
globals in its own process. Declarations and repository bindings are not in the journal (Release 2
recovery). **For the lead's decision:** a declaration names one file and its bytes, so an owning
service attaches only from that copy as it was when it first declared. An upgraded module, or the
same module run from another checkout's installed `.veldo/` copy against a shared store, is refused
`ownership_conflict` at attach (the suite observes this as `owned-code-copy-attach`), and Release 1
has no re-declaration path. That is the brief's design taken literally; if the authority must
survive an upgrade, the binding needs an operator re-declaration step. The repository binding has
the same shape: moving the accepted repository on disk refuses every service until it is rebound,
and no rebinding path exists.

**Consequences for callers.** `declare_owners` requires `module=` (the owning module's own
`__file__`); `entity_owners` rows carry `module` and `module_digest`. New refusals:
`repository_binding_conflict` (`invalid_input`), `foreign_transition` (`missing_authority`), and
`unenrolled_commit` from `accept_revision`. A kind's `floor_commits` now lists only the accepted
commits the bound repository holds (superseded: since the recorded-numbers fix it lists every
accepted commit). `control_store.py` imports nothing new, since VELDO-0023's AC3
row pins its imports. Every control-store suite is green after the change (`36`, `37`, `38`, `39`,
`46`, `56`, `58_veldo_0035`, `58_veldo_0036`, `59`, each re-run on f84f2d2 with `--suite`), and
`check_teeth_mutations.py --finding 35` still rejects all 12 of VELDO-0035's mutants. `56_veldo_0027_signing`'s
`signing/process-count-and-listeners` row failed twice inside this worktree mid-change (once with
the second fix stashed), passed in a copy of the same tracked tree at 9930b32, 3fb2115 and the
working state, and passed in this worktree on the final code and again on its re-run; its cause was not determined, and the
row reads only VELDO-0027's own signer processes.

### Re-running the third check's scripts

`review3-rerun.txt` is the output of every script against the modules after the recorded-numbers
fix (6c60f11; the same run against f84f2d2 differed only in the two lines named below), with each
script's exit status, and `review3-rerun.diff` every change made to them, generated against the
reviewer's originals: (a) every path to the reviewer's scratch directory, including the one the `p5`
child process imports its harness from, now names one scratch directory (`<probe>`) whose harness
loads this worktree's `.veldo/`; `p6`'s old store copy there is byte-identical to
`git show 9421af6:.veldo/control_store.py`; (b) `p4` and `p5` call `declare_owners` without `module=`
and insert four-column owner rows, so they stop at that call as written (exit 1); `p4a` and `p5a` add
`module=` and the two digest columns and change nothing else; (c) `p3` and `p3b` stop at
`attach_revisions`, which now refuses the other repository (exit 1), so `p3a` and `p3ba` catch that
refusal and then register `accept_revision`'s own code without attach, which is what the transition
check answers. `p3a` keeps the reviewer's BUG condition (enabling afterwards refuses) with a shorter
message and drops the reviewer's two recovery attempts (retire, move back), since nothing is left to
recover. `q7_lost_commit` is the builder's probe for the finding above, not the reviewer's.
An earlier record of this re-run (replaced) ran `p5`'s child process against the reviewer's old
modules, because only the parent's import path had been changed.

| Script | Result on the final code |
|---|---|
| `p1_generic` | every write the reviewer's BUG conditions name refused (`entity_owned`, `unregistered_inputs`, `invalid_input`); the case-variant and unowned writes, which own nothing, commit; counter unchanged at 1; no BUG line. Since the recorded-numbers fix `accept_revision-new-at-alias-prefix` refuses `stale_version` before ownership is read (the reviewer's command declares no version for the carrier record the transition writes); at f84f2d2 it refused `entity_owned` |
| `p2_names` | self-registered `enable_artifact_kind` and `accept_revision` refused `foreign_transition`, counter unchanged; no BUG line |
| `p3`, `p3a` | `p3` stops at its attach to the unrelated repository, refused `repository_binding_conflict`; `p3a` catches that refusal, then direct `accept_revision` of its commit refused `unenrolled_commit`; enabling afterwards commits; no BUG line |
| `p3b`, `p3ba` | `p3b` stops at its attach to the clone, refused `repository_binding_conflict`; in `p3ba` its unpushed commit refused `unenrolled_commit`; once fetched into the bound repository it is accepted and enabling commits; no BUG line |
| `p4` | stops at its first `declare_owners` call, refused `malformed_command` for the missing `module=` |
| `p4a` | every squatting or malformed declaration refused `malformed_command` (each names `upsert_entity` or is empty), so generic writes stay refused `entity_owned`; the rightful attach succeeds; redeclaring the same is a no-op; a read-set attach over pre-written snapshots refuses `ownership_conflict`; after deleting the table by raw SQL a generic write commits and the owner's reattach refuses `ownership_conflict` (stated limit); no BUG line |
| `p5` | its first case prints the child's declaration refused `malformed_command` (no `module=`), then it stops at the four-column insert |
| `p5a` | a declaration during an in-flight write of the kind refuses `ownership_conflict`; a write while a declaration is in flight is refused `entity_owned` after it commits; no BUG line |
| `p6_rawsql_oldcopy` | the 9421af6 store copy and raw SQL both rewind the counter: the one `BUG(limit)` line left, a stated limit; `entity_owners` is not a replay state part |
| `q7_lost_commit` | enabling after the bound repository lost an accepted commit commits with `next = 10` and both commits in `floor_commits`; at f84f2d2 it printed its FINDING line with `next = 1` |

### Gate cost after the third check

`timing.json` (rewritten by `drive.py`): the suite runs in 3.8 s in process under the proof driver
and 3.9 s under `selftest.py --suite` (34 rows, 60 assertions with the shared preamble); the gate
runs it twice. By comparison with the second review's 3.4 to 3.6 s, the two new rows cost roughly
0.3 to 0.5 s. The 42 finding-37 cases take 652.9 s serial for baseline, no-op and mutant runs; `check_teeth_mutations.py --finding 37` took 6 min 20 s serial
here, up from 3 min 57 s for 34 cases. **Note for the lead:** `check_gate_mutations.py` was run once
on this tree at 1d80e77 as a measurement, not as verification, while other builders were running
(load average 11.6 on 20 cores). It stopped at its combined 120 s deadline
(`mutation_budget_exceeded`) with 158 registered cases, 42 of them finding 37. The contention means
this measurement does not say how much of that is this branch, but a serial run may exceed the
budget too, and the stage's budget, or finding 37's share of it, is the lead's decision.
(Superseded: after the merge of origin/main the budget scales with the inventory; see the last
section.)

## Recorded numbers (2026-09-23)

**The lead's decision.** The floor must not depend on Git keeping a commit. `accept_revision`
records, when it accepts a commit, what the floor needs from that commit, and the floor reads the
record, so a branch deleted, pruned or force-pushed afterwards changes nothing. A revision recorded
before this rule, whose commit the bound repository no longer holds, is refused by name at
enabling, never skipped. Refusing at acceptance a commit the bound repository does not hold stays
as it was.

**What is recorded, and why it is paths, not numbers.** A kind's numbers depend on its template and
prefix, and the first revision of a repository is always accepted before any kind can be enabled,
because enabling names an accepted revision. So acceptance records the Git half of today's
derivation and enabling does the rest: `control_readset.carrier_paths` lists every path of the
commit's tree and whole history (`ls-tree -r` and `log -m --no-renames --name-only`, no pathspec)
that holds a digit, since a carrier always holds its number's digits; `control_alias` applies the
kind's carrier pattern to that list (`maximum`). The legacy path uses the same function against
Git, so there is one derivation. Dropping the kind's `:(icase)` pathspec only widens what the walk
lists, and the carrier pattern filters the same way: over this repository's own history (580
commits) the old and new derivations give identical floors for seven templates (`VELDO` 132, `WARP`
1711, `PLAN` 20, `proof/{alias}/README.md` 123, and three that hold nothing).

**Where it is recorded.** In its own entity, not inside the `accepted_revision` record:
`accepted-carriers/<repository>/<commit>`, kind `accepted_carriers`, holding the domain,
repository, commit id and paths. It is written by the same `accept_revision` command, in the same
transaction and journal record as the revision, the first time a commit is accepted, and it is
immutable after that (a record already there is only checked to belong to that commit). Both the
kind and the id prefix are declared store-owned by `accept_revision` in `REVISION_KINDS` and the
new `REVISION_PREFIXES`, by `attach_revisions` and by `control_alias.attach`. Keeping it out of the
revision record leaves VELDO-0035's accepted-revision shape unchanged, and matters because
VELDO-0035 snapshots embed the whole revision entity in every snapshot they accept.

**Enabling.** For every accepted commit of the repository: a record present means the kind's floor
comes from it and Git is not read; no record and the bound repository holds the commit means Git is
read as before; no record and no commit means `accepted_revision_unavailable` (taxonomy
`missing_authority`), naming the commit and the bound repository, and nothing is written. The
`floor_commits` of a kind now list every accepted commit again. One Git read is left in enabling:
the NAMED revision's root commits are still checked against the enrolled repository, so naming a
revision whose own commit is gone refuses `wrong_repository` (closed, not open).

**What clears an `accepted_revision_unavailable`: none needed, because none exists outside test
stores.** `accept_revision` and its record were both introduced on this branch, and every revision
it writes now carries its record. One written around the commands (raw SQL, as rows 14 and 16 do)
is the stated same-account limit, and Release 1 has no operator path to retire an accepted revision
(`retire_entity` is refused `entity_owned`, and moving the revision forward needs its old commit to
check descent). This is in the specification's Notes.

| Row | At f84f2d2 (recorded RED, `red-at-f84f2d2.json`) | Now |
|---|---|---|
| `aliases/floor-from-recorded-numbers` (new, row 16) | the side revision holding VELDO-0009, accepted and then lost to a deleted, pruned branch, dropped out: enabling committed with `next = 1` and allocated VELDO-0001; a raw-SQL legacy revision whose commit was then pruned was skipped, and the decision kind enabled | `next = 10`, VELDO-0010 allocated; the legacy revision is read from Git while held (plan `next = 6`) and, once pruned, enabling refuses `accepted_revision_unavailable` naming the commit, and no decision kind exists |
| `aliases/revision-in-enrolled-repository` (row 14, expectation changed by this decision) | the raw-SQL revision naming the unrelated repository's commit was skipped and the plan kind enabled beside it | enabling refuses `accepted_revision_unavailable` and no plan kind exists; with that revision removed, the plan kind enables and its `floor_commits` hold the clone's commit and not the foreign one |

`red_at_f84f2d2.py` runs the final suite with `control_alias.py`, `control_store.py` and
`control_readset.py` from f84f2d2 and everything else from this tree, with no shims; the suite
completes and exactly those two rows fail.

**Mutations.** 44 finding-37 cases now (`mutations.json`, all rejected, every diff re-derived and
byte-identical to what `check_teeth_mutations.py --diff-dir` writes). New, each reddening
`aliases/floor-from-recorded-numbers` by a failed assertion with the baseline and a no-op copy green:
`floor-rederives-ignoring-record` (enabling ignores the record; the lost recorded commit is then
refused), `legacy-lost-commit-skipped` (the refusal becomes a skip, reintroducing f84f2d2's
behavior; it also reds row 14), and `acceptance-records-no-paths` (acceptance records an empty
list). Changed because the code they mutate moved: `alias-floor-ignores-history` now drops the
history walk in `carrier_paths`, where the history is read, and still reds only
`aliases/historical-floor`; `alias-floor-named-revision-only` is re-anchored to the new `commits`
line. Removed because their code no longer exists: `floor-counts-unheld-revisions` (the skip) and
`alias-floor-pathspec-case-sensitive` (the pathspec). The second takes a distinct replacement,
`alias-floor-carrier-case-sensitive` (the carrier pattern loses `re.IGNORECASE`), which reds
`aliases/floor-counts-every-carrier`.

**Probes.** `q7_lost_commit` now enables with `next = 10` and both commits in `floor_commits`, with
no FINDING line. Every other line of `review3-rerun.txt` is as before, apart from two traceback
line numbers and random commit ids, except `p1`'s one noted in the table above; `p6`'s `BUG(limit)` is still the only BUG line.

**Cost of the record, measured.** On this repository's own HEAD (580 commits) `carrier_paths` takes
29 ms and records 1588 paths, 69 KB of JSON, once per newly accepted commit, in the entity and in
its journal record. Each record lists the whole history, so a store that accepts every commit of a
growing repository grows roughly with the square of the history. If that matters, a record could
hold only what a descendant adds over the commit it moves the revision from, with the floor reading
every record of the repository; that was not built here.

**Merge, and consequences for callers.** The branch merged origin/main (97b6961) for the scaled
mutation budget, keeping both sides of the scaffold's runtime assets (`control_enrollment.py` listed
once), the suite manifest and the mutation registry (findings 25, 31, 46 and 64 beside 37), with
`requires.json` regenerated by `run_scope.py --emit-requires`. Callers: `accept_revision` writes a
second entity the first time it accepts a commit, so a command built by hand must declare its
expected version (the reviewer's `p1` command does not, and is refused `stale_version`); new refusal
`accepted_revision_unavailable`. Every control-store suite is green on the final code (`36`, `37`,
`38`, `39`, `46`, `56`, `58_veldo_0035`, `58_veldo_0036`, `59`), so are the suites that read
`init_scaffold._FILES` (`01`, `03`, `08`, `11`, `12`, `13`, `14`, `26`) after the merge, and
`check_teeth_mutations.py --finding 35` still rejects all 12.

**Gate cost.** `check_teeth_mutations.py --finding 37` took 556.7 s wall, serial, for 44 cases
(load average 4.5 to 7 on 20 cores during the run); `drive.py` took 965.6 s and records 722.7 s of
serial baseline, no-op and mutant runs (`timing.json`). The suite runs in 4.2 to 6.2 s under
`selftest.py --suite` (6.2 s at load average 12), 4.5 s in process under `drive.py`.
`check_gate_mutations.py`, run once as a measurement at load average 12.8 to 13.3, passed: 235
registered, 235 executed and rejected, 303 workers, 196.8 s against its scaled budget of 470 s
(`budget_for(235)`, 2 s per case).

