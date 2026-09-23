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
  59_veldo_0037_aliases   27 passed   2.25s
  selftest (PARTIAL, 1 of 67 suites): 53 passed, 0 failed
python3 -B scripts/check_teeth_mutations.py --finding 37
  {"mutations_rejected": 24, "green_suites": {"59_veldo_0037_aliases.py": 53}}
python3 .veldo/validate.py all        exit 0
bash scripts/check_generated.sh       generated: pass
python3 -B proof/VELDO-0037/red_at_adfb89a.py
  the eight review-defect rows, and only they, fail against adfb89a's modules
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
again. A `Publisher` is bound to the repository its checkout's root commits identify. Both modules are installed by
`_FILES` in both copies of `init_scaffold.py`; they are runtime assets, not validator imports, so
they are not `REQUIRED_SUBSTRATE`. Canonical `engine/.veldo` files and installed `.veldo` copies are
byte-identical. The store, its schema, `control_snapshot.py`, `claim.py` and `git_process.py` are
consumed unchanged. No dependency is missing on main, so no seam was added outside the footprint.

## Criteria and observed rows

Suite `scripts/suites/59_veldo_0037_aliases.py`, 27 rows (19 below, 8 in the review section). It uses a real SQLite store, a real Git
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
`control_store`, outside this footprint. The template overlap walk over-approximates (it ignores a
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
