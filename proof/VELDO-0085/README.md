# VELDO-0085 decomposition publication proof

The signed publication service renders complete specifications using the authority's
alias counter and the shared document writer. The backlog binds each published
specification revision to its declared unit and one owning item. Admission and
eligibility recheck the accepted bytes; appended units need fresh priority.

## Criterion rows

| Criterion | Rows | Observations |
| --- | --- | --- |
| AC1 | fields/invalid-id-no-artifact | Every required field and invalid unit ID is refused before the counter, store or filesystem changes. |
| AC1 | binding/one-owner | Real prepare and admission bind one primary alias/revision and one item. Cross-item publication and preparation, and two units sharing an active primary revision, refuse. |
| AC1 | priority/fresh-growth | A published appended unit remains PLANNED while its approved sibling continues. The owner's renewed priority makes it executable. |
| AC2 | aliases/authority-counter | Identical source tuples reuse their alias. Different source IDs, revisions and roles advance the SQLite counter and retain exact mappings. Historical WARP and VELDO files stay byte-identical. |
| AC3 | dependencies/eligibility | Generated specification dependencies and execution-unit edges agree. The real eligibility service refuses the unresolved dependency while accepting the independent unit. |
| AC3 | publication/other-process | A separate process reads the real store and files, comparing complete bytes, digests, versions, ownership and dependency edges. |
| AC3 | publication/stale-input | Local edits refuse preparation and execution. Even grooming and approving local bytes cannot admit them. A newer accepted but unpublished document refuses preparation. |
| Installation | install/assets | Both new modules are scaffolded; changed engine and installed copies are identical. |

Every unit, document, admission, priority and dependency under test is produced by
its production interface. Fixtures use real SQLite, Git, generated OpenSSH keys,
signed commands, enrolled publication and loopback HTTP. No model, real credential,
remote service or user service manager is used.

## Red record and mutations

`red-at-7df42187.json` runs the current suite against an unchanged archive of the
pre-change commit. Every behavior row fails by assertion, with one report per row.
The absent publication service is a failed assertion, not an import exception.

Finding 85 registers the three declared falsifiers: an artifact reserved before
unit-ID validation, allocation from the checkout maximum, and an omitted generated
specification dependency. Additional mutations cover ownership, a shared primary
revision, premature readiness after append, lost execution dependency, stale bytes,
unpublished input, admission, eligibility and installation. `mutations.json` records
baseline and no-op controls, actual failing rows, source digests and the applied
diff for every mutation. All 12 named mutations fail by assertion, without raised regions.

Reproduction uses `scripts/drive.py` for both the red record and mutation evidence;
`scripts/check_teeth_mutations.py` independently drives finding 85 with two jobs.

## Validation and limits

`suites.json` records these 13 suites run normally and under the supplied empty gate
environment: `01_warp_0101_reviewer_notes`, `03_plugin_extension_loading_runner`,
`26_veldo_0009_install_stamp`, `30_veldo_0017_entity_lifecycle`, `50_git_environment`,
`51_parser_boundary`, `52_writer_boundary`, `59_veldo_0037_aliases`,
`60_veldo_0052_eligibility`, `60_veldo_0053_architecture`, `73_veldo_0078_backlog`,
`76_veldo_0079_grooming` and `82_veldo_0085_decomposition`. Each selftest invocation is a partial run and intentionally exits 2
when its assertions pass. These observations are not a full gate stamp.

The publication path binds authority documents. Historical file-only specifications
retain their existing admission behavior. Recovery and concurrent-author matrices
remain deferred by the specification. This change records no independent review or
approval. The full gate was not run, as instructed; nothing was pushed. The mutation coordinator
suite `53_veldo_0123_mutations` was also not run because it executes fixture copies of
`scripts/verify.sh`; the registered finding was driven directly instead.

Repository validation passes. The footprint checker reports no outside paths, the
mutation anchor checker reports zero bad anchors, and the gate byproducts are excluded.
