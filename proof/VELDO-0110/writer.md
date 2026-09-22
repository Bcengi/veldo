# One document writer

The write-side continuation starts at 23e1a2b on one-parser. The shared writer
lives beside the strict reader in `.veldo/yamlish.py`; both init lists already
include that module. Its engine copy is byte-identical.

`dump(mapping)` emits a nonempty mapping with string keys and recursively nested
strings, integers, nulls, lists, and mappings. This is the existing reader's
value domain: boolean, float, and date spellings remain strings. Python booleans,
floats, non-string keys, lone surrogates, cycles, and unsupported roots refuse
explicitly rather than changing type. Empty nested collections and nulls survive.
`render_document(mapping, body)` adds front matter and retains the supplied body.
The reader's grammar and coercion rules are unchanged.

Every string value is double quoted. Escapes preserve controls, whitespace,
newlines, punctuation, and all Unicode scalar values, including astral code
points. Quoting does not ask our reader whether a plain scalar looks safe.
Tracker intake applies the original `_fm_safe` guard before serialization; the
new property compares its exact source with 23e1a2b and tests its behavior over
the generated string corpus. Sanitization remains deliberately lossy at that
trust boundary; the shared serializer itself is lossless.

Spec and plan intake share one adapter. Estimate/reconciliation records, era
shifts, incident drafts, restoration drafts, and tripwire drafts also delegate
to the shared writer. Schema validation and source-preserving field edits remain
with their owners. The source boundary detects named and renamed former writers,
including generic key/value loops and direct interpolated documents. As with the
reader boundary, this is a source check, not a proof about arbitrary Python.
Commit trailers and test fixtures are separate, explicitly scoped surfaces.

Suite 52 runs generated value and nested-structure round trips, with PyYAML as an
independent oracle. It also starts from PyYAML-generated documents, decodes them
with PyYAML, and re-emits their values through our writer to both readers. Oracle
rows skip by name when PyYAML is absent. The old unquoted `true` defect is driven
as a negative control: our reader agrees with the input string while PyYAML
returns a boolean. Planted second writers fail the boundary; delegation passes.

`python3 scripts/writer_corpus_audit.py proof/VELDO-0110/writer-corpus.json`
reproduces the corpus report. It inventories every baseline path plus current
specs/plans, reads today's files with the strict reader, and compares re-emission
against both readers with exact field, type, and value diagnostics. It does not
rewrite the input corpus. The prose-only index has no metadata to serialize and
is recorded separately. The JSON records input and output hashes for every path.

Full-gate results for this continuation are recorded separately after execution.
