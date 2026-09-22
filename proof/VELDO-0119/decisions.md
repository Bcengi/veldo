# Decisions before implementation

Baseline reader and corpus: b34d17d. Every one of the 218 historical records
is assigned by file and 1-based line in dispositions.jsonl, retaining the
input SHA-256. No record is filtered, including duplicate byte witnesses.

- blank-block-clip: 200 records, disposition (a). The grammar names literal
  and folded blocks with clip/strip/keep chomping. Clip retains a content
  line's final break, not an empty block's trailing empty lines. The reader
  incorrectly returns a newline for an all-blank clipped block. Fix reader.
- empty-flow-map: 15 records, disposition (a). The grammar explicitly allows
  empty scalar values in mappings, including flow mappings. Accept an empty
  mapping value before comma or closing brace; keep empty sequence entries
  refused. Fix reader.
- literal-del: 3 records, disposition (c). The existing written grammar's
  lexical section explicitly permits literal DEL in plain and continuation
  styles, and explicitly records that PyYAML rejects it. Preserve that
  domain verbatim. Extend the independent fixture adapter to observe a
  length-preserving printable substitution with the external parser and
  invert that substitution in its node tree before adaptation. Retain the
  original invalid-YAML observation alongside the supplementary observation;
  never equate raw YAML refusal with dialect refusal for this documented
  extension. No production reader change and no target or input changes.

Booleans, null-like words and leading-zero spellings already have the
written rule: only canonical decimal integers become integers; other plain
words stay strings. The existing style/spelling adapter handles them. They
are not among the 218 disagreements; retain their raw tags in observations.

The frozen xz (ASCII base64 envelope) records every tracked YAML/YML document and every Markdown
front-matter outcome, including absent metadata and refusals, for both copies.
This conservative superset includes all specs, plans, manifests, substrate
records, templates and the owner's policy. It includes parsed source (decoded UTF-8 with optional BOM), input digests
and complete trees, with shared objects deduplicated. Unread Markdown prose
is omitted; absent-metadata documents retain an empty parser input.
After each reader fix compare these same inputs; report every changed answer
in full, and stop before committing if the owner's policy changes.
