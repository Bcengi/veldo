# One document reader

Requested on branch one-parser against 34342c3. The user request is the work contract:
strict standard-library parsing, corpus measurement before caller migration, one syntax
boundary, mirrored engine substrate, and a full gate before completion. No deployment,
merge, push, or independent approval is represented by this work.

## Sequence and evidence

1. 6b2135a adds only the reader, its engine mirror, and behavior tests.
2. 62d338b commits the comparison of all 331 specifications and plans, before any
   caller or document migration. `corpus-before.json` records all input hashes,
   differences by reader and field, and refusals. `corpus-before.md` lists refusals.
   `python3 scripts/parser_corpus_audit.py` reproduces this report from the frozen
   input and reader commits, even after migration; it does not measure edited inputs
   and label them as the original corpus.
3. Caller and document migration follows that report. `document-migration.json`
   records the explicitly rewritten fields and their retained values. The capability
   manifest's note strings are additionally quoted directly from their source: the
   old flow parser split their commas into invented fields. The old capability
   consumers explicitly avoided that parser for precisely these prose notes.
4. The boundary check and its regression tests follow migration.

## Reading decisions

Literal prose is quoted when it contains hashes, colons, punctuation that looks like
flow syntax, or continuation lines that look like nested keys. This retains the old
full reader's prose instead of silently truncating it at a comment. Status and risk
annotations are comments, not enum values. Quoted scalars lose their delimiters;
structured front matter produces actual lists and mappings for every caller.

Literal and folded block scalars now produce their text, including the declared
chomping behavior. The old reader returned the `>` marker as part of the string and
flattened literal blocks. Those are intentional corrections to the reader's answer;
the block syntax in the documents needs no rewrite. The historical comparison records
each correction, including fields in otherwise unchanged documents.

No unsupported shape is interpreted as absence. Tags, anchors, aliases, directives,
multiple documents, multiline quoted scalars and explicit block indentation indicators
are refused. An actual missing front-matter region is distinct from an unclosed fence,
a sequence in place of a mapping, or unreadable metadata. Policy readers retain only
their schema checks: boolean spellings, required mappings, and commit-ID constraints.

Ambiguous syntax is refused by the reader. The corpus rewrites make the affected prose
explicit using its previously recorded full value; they do not introduce a heuristic
into the reader. No historical proof digest or review approval has been rewritten to
claim that the modified documents were reviewed in the past.

The shared reader is in both init lists (laid files and required substrate). All
changed engine runtime files have matching repository copies. Writer fixes are part
of the migration: tracker intake and incident drafts must emit readable syntax too.
