# VELDO-0164 implementation and verification record

Built from 294e1933 on agent/codex/veldo-0164. The specification remains ready.
No gate, mutation harness, push, merge, service activation or external account ran.
This is builder evidence, not independent approval or a merged-tree verification stamp.

## Operational criteria

| Criterion | Behavior observed | Proving rows | Declared falsifier |
| --- | --- | --- | --- |
| AC1 | An A member receives exactly the A records of every registered project kind, shared role and tool configurations and the default team. B and projectless records are withheld. Workflow reads use the repository scope checked for editing. | reads/registration, reads/member-A, reads/workflow, reads/team-route, reads/no-project, reads/withheld-problems, reads/rule-variants | v164-model-unfiltered removes the scope argument at the authority read; reads/member-A must fail on B records. |
| AC2 | A-only records and the A half of mixed records are delivered. Other members' revocations and B publications are withheld. Own revocations remain visible. Head watermark and publication freshness remain unchanged, and cursors pass hidden records. | events/member-A, events/registration, events/publication, events/own-revocations, events/cursor, events/edge-unchanged | v164-events-unfiltered retains every journal change; events/member-A must fail on B records. |
| AC3 | Universal readers retain all entities, problems, redactions, machines, workflow revisions and journal records, including unrouted proposals and account policies. | owner/unchanged | v164-universal-projectless-hidden removes the universal exception for projectless data; owner/unchanged must fail on unrouted intake. |

The three declared falsifiers and seven additional negative controls are registered
as finding 164 in scripts/check_teeth_mutations.py. falsifiers.json binds their
exact diffs to production source hashes and names the expected failing rows.
anchors.py only evaluates registry declarations and checks exact replacement anchors;
it neither invokes the mutation harness nor executes a mutant. Execution and rejection
of these falsifiers remain reviewer work. Existing affected finding 130 anchors were
updated for the expanded kind registrations and filtered entity variable, preserving
their original defects and expected assertions.

## Implementation boundaries

Each Kind declares its project rule beside its writer. The new scope resolver reads
fields, unit or request references, or the projects whose execution_repository matches
a repository record. Repository-wide data requires coverage of every project sharing
that repository. Workflow revisions use their repository name directly, as their
editor check does. Assignment scopes must be covered in full. Unresolved references,
unregistered kinds and account policies are universal-only. An AWAITING_ROUTE intake
proposal remains projectless even if its holding area is the factory project.

Filtering precedes integrity validation and redaction, so hidden rows cannot leak
through problem identities, redaction paths or derived machines. Current membership,
model data and project references are read in one authority read transaction.
Observations contain principal, model or cursor, scope, watermark and counts by reason,
never withheld identities. Member feeds retain published events only for visible
receipt entities. The edge feed remains unfiltered for session revocation.

The separate team GET now uses the scoped configuration model. Member event answers
carry a consumed journal cursor; the stream uses it even on an empty page, so a hidden
page cannot stall delivery or cause later visible records to be skipped. Universal
answers and the edge feed retain their old representation. These two API changes are
recorded in the specification footprint without changing any criterion.

## Test method and results

Run each named suite through scripts/selftest.py with its suite selector, one at a
time. Suite 103 has 16 behavior rows. It uses a real SQLite control store, actual signed
journal commits with a generated OpenSSH key, the real authority lock, real stored
workflow revisions saved by Workflows.save, and the actual publication journal and log
readers. Other entity rows are trusted-store seeds shaped like their owning writers;
they do not certify those writers' admission policies. Default team seeds use the
VELDO-0162 kind, revision identity and head. Published event seeds exercise the actual
bounded log reader, not the landing publisher's acceptance checks. No live engine runs.

legacy.py retains verbatim reader function bodies extracted from 294e1933. The old
read_model body uses the current kind registration, including the newly published
default team, to compare behavior over the same entity universe. The old workflow and
feed functions compare complete answers. The suite compares the full seeded journal
as well as the explicit A, B, mixed and other-member revocation sequence.

| Suite | Result | Kept output |
| --- | --- | --- |
| 103_veldo_0164_scoped_reads | 16 suite rows passed, zero failures; 42 including shared checks | suite.log |
| 65_veldo_0132_workflow | 16 suite rows passed, zero failures; 42 including shared checks | regression-0132.log |
| 71_veldo_0130_api | Aborted during service fixture construction: unavailable_service:profile:user_manager | regression-0130.log |
| 94_veldo_0162_configuration_routes | 25 rows fail after setup refuses unavailable_service:profile:user_manager; one format row passes | regression-0162.log |
| 93_veldo_0152_intake_routes | 11 pass, 11 fail; routing cycles report runtime_unavailable | regression-0152.log |
| 82_veldo_0141_execution_record | Aborted creating its fixture under /run/user/1000: PermissionError | regression-0141.log |

Passing selected suites exit 2 by the repository's partial-run contract. These results
are not a passed unit gate. The manifest leaves acceptance and required evidence pending
until the reviewer can run the blocked regressions, falsifiers and merged-tree gate.
No check was weakened to accommodate this environment. Initial scope-suite failures
were fixture mistakes: workflow ownership registration, a missing default-team head,
and an incorrectly composed legacy-reader namespace. The corrected fixture passes;
suite-initial.log and suite-second.log retain those development runs.
