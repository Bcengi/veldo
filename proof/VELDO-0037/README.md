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
  59_veldo_0037_aliases   19 passed   0.78s
  selftest (PARTIAL, 1 of 67 suites): 45 passed, 0 failed
python3 -B scripts/check_teeth_mutations.py --finding 37
  {"mutations_rejected": 8, "green_suites": {"59_veldo_0037_aliases.py": 45}}
python3 .veldo/validate.py all        exit 0
bash scripts/check_generated.sh       generated: pass
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

Authority startup calls `control_alias.attach(store, conn, domain_uuid, repository_uuids)`. A kind
is enabled once per repository with its first number taken from an exact accepted commit
(`accepted_maximum`, C9); allocation never reads any tree again. Both modules are installed by
`_FILES` in both copies of `init_scaffold.py`; they are runtime assets, not validator imports, so
they are not `REQUIRED_SUBSTRATE`. Canonical `engine/.veldo` files and installed `.veldo` copies are
byte-identical. The store, its schema, `control_snapshot.py`, `claim.py` and `git_process.py` are
consumed unchanged. No dependency is missing on main, so no seam was added outside the footprint.

## Criteria and observed rows

Suite `scripts/suites/59_veldo_0037_aliases.py`, 19 rows. It uses a real SQLite store, a real Git
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
| AC3 declared falsifier | `publication-altered-bytes` | altered bytes are written and recorded under the accepted digest; the independent reader refuses `document_mismatch` | `publication/accepted-documents` |
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

`timing.json`: the suite runs in 0.85 s in process (0.78 s under `selftest.py --suite`); the gate
runs it twice (unit and first-use integration). The eight mutation cases take 21.2 s serial for
baseline, no-op and mutant runs; the gate shares baseline and no-op controls per suite and module
(2 groups) and runs 8 workers in parallel, so its added wall time is lower. Conservative added
workload: about **23 s**, under the 60 s limit. Note for the lead: `check_gate_mutations.py` has a
combined 120 s stage budget, now across 124 registered cases (both drivers). Proof is readable JSON, Markdown,
Python and eight small diffs (under 100 KB), with no keys, signatures, encoded blobs, bytecode or
gate logs.
