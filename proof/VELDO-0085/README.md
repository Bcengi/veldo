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
| AC1 | refusals/service-class | Scope, duplicate unit, empty holders and bad specification ID return named refusals, observations and counts by reason through the separately loaded backlog service. |
| AC3 | dependencies/current-specification | Twin source revisions supersede the first alias, and the dependent names the current alias. |
| AC3 | dependencies/prepare-mismatch | Production prepare refuses a dependency superseded after publication as binding_mismatch:dependency_specification. |
| AC3 | publication/concurrent-current | Two independent SQLite connections start with the same counter; both publications materialize and the later authority commit leaves exactly one current specification. |
| Installation | install/assets | Both new modules are scaffolded; changed engine and installed copies are identical. |

Every unit, document, admission, priority and dependency under test is produced by
its production interface. Fixtures use real SQLite, Git, generated OpenSSH keys,
signed commands, enrolled publication and loopback HTTP. No model, real credential,
remote service or user service manager is used.

## Red record and mutations

`red-at-580b19e2.json` runs the current suite over the unchanged review base.
The four new rows fail by assertion on their observed behavior, with no raised
regions. The eight original rows remain green. No row needs an added module on
this base: it already includes the publication service and binding reader.

`red-at-7df42187.json` is also regenerated over the unchanged original pre-build
base. All twelve rows fail by assertion because this older tree has no publication
service. Those rows require the new `control_decomposition.py` and
`control_decomposition_binding.py` modules to exercise their production journeys;
this older record alone is not evidence of the review findings.

Finding 85 retains the twelve original mutations and adds four globally unique
names: `decomposition-private-refusal-class-only`,
`decomposition-first-specification-match`, `decomposition-prepare-dependency-unchecked`
and `decomposition-supersession-omitted`. The first restores a private backlog
module so the passed service's refusal class escapes its catch. The remaining
three select the first historical alias, omit prepare's dependency comparison,
and omit authority supersession respectively. Every named row turns red by assertion.

`mutations.json` records the baseline and byte-identical no-op controls, actual
failing rows, source digests and all sixteen applied diffs. Reproduction uses
`scripts/drive.py` for the red records and detailed mutation evidence, and
`python3 scripts/check_teeth_mutations.py --finding 85 --jobs 2` for the independent
registry run.

## Validation and limits

`suites.json` records these 13 suites run normally and under the supplied empty gate
environment: `01_warp_0101_reviewer_notes`, `03_plugin_extension_loading_runner`,
`26_veldo_0009_install_stamp`, `30_veldo_0017_entity_lifecycle`, `50_git_environment`,
`51_parser_boundary`, `52_writer_boundary`, `59_veldo_0037_aliases`,
`60_veldo_0052_eligibility`, `60_veldo_0053_architecture`, `73_veldo_0078_backlog`,
`76_veldo_0079_grooming` and `82_veldo_0085_decomposition`. Each selftest invocation is a partial run and intentionally exits 2
when its assertions pass. These observations are not a full gate stamp.

The publication path binds authority documents. Historical file-only specifications
retain their existing admission behavior. Recovery and broader concurrent-author matrices
remain deferred by the specification; this review adds the bounded two-publisher
supersession row. The five filed limitations are listed in the specification's
History. This change records no independent review or approval, and nothing was
pushed. The repository gate was not invoked.

Review validation results and the final whole-selftest result are recorded in
`review-checks.json` with their retained logs. The earlier `suites.json` describes
only the original implementation's partial runs.

Whole-run result: `selftest: 6872 passed, 0 failed`. All sixteen mutations were rejected, with
green baseline and no-op controls and no raised regions.
