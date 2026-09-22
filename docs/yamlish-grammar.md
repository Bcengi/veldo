# Shared document reader grammar

Revision: `veldo.yamlish-grammar/1`. This is a test fixture contract, independent
of the implementation. The machine-readable partitions and bounds are in
`scripts/fixtures/yamlish_grammar.json`. Changing either file changes the
fixture identity. No production module imports the fixture.

```ebnf
document       = block-map | block-sequence ;
value          = scalar | block-map | block-sequence | flow-map | flow-sequence ;
block-map      = member, { newline, member } ;
member         = key, ":", ( " ", inline | newline, indent, value ) ;
block-sequence = item, { newline, item } ;
item           = "-", ( " ", inline | newline, indent, value ) ;
inline         = scalar | flow-map | flow-sequence ;
flow-map       = "{", [ pair, { ", ", pair } ], "}" ;
pair           = key, ": ", flow-value ;
flow-sequence  = "[", [ flow-value, { ", ", flow-value } ], "]" ;
flow-value     = flow-map | flow-sequence | plain | single | double | empty ;
scalar         = empty | plain | single | double | literal | folded
               | continuation | escape ;
empty          = "" ;
single         = "'", { character | "''" }, "'" ;
double         = '"', { character | escape }, '"' ;
escape         = '"', "\\", escape-name, '"' ;
literal        = "|", chomp, newline, indent, payload ;
folded         = ">", chomp, newline, indent, payload ;
chomp          = "" | "-" | "+" ;
continuation   = plain, newline, indent, plain,
                 [ newline, indent, plain ] ;
key            = identifier | path | single-key | double-key ;
identifier     = letter-or-underscore, { letter-or-digit-or-underscore } ;
path           = letter-or-dot-or-underscore, { identifier-character | "/" | "-" | "." } ;
newline        = LF | CRLF ;
indent         = one-space | two-spaces ;
comment        = "" | " # c" ;
```

The document root counts as a value node; keys do not. Root depth is zero.
The baseline includes one through three nodes, depth at most two, and at
most two children per container. Empty collections are flow productions.
Block collections require at least one child. Inline sequence mappings and
wrapped flow collections are separate multiline witnesses, with their
shortest form and one extra continuation, including witnesses outside the
node bound. Those witnesses are reported separately, never substituted for
the exhaustive base domain.

Payloads enumerate every word of length zero, one, and two over the six
characters in the data file, then every named lexical partition. Duplicate
payloads and duplicate source bytes retain distinct derivation identities.
Keys enumerate the declared representatives of identifier, path and both
quoted classes; a mapping's keys must have distinct decoded spellings.
There are at most two keys in a baseline derivation. Each occurrence chooses
its own scalar style and payload. Indentation, newline and trailing comment
are document-wide independent choices. Comments attach to syntax headers,
never block content. Every document has a final newline. A future larger
qualification domain must be explicit; the baseline is never sampled.

Plain words must be nonempty, have no leading or trailing whitespace, not
start with a YAML indicator, and contain neither whitespace followed by `#`
nor a colon followed by whitespace or end of word. Flow plain words also
exclude flow punctuation. Single quotes double apostrophes. Double quotes
escape quotes, backslashes and control characters. Literal and folded
payloads retain their literal spelling, and enumerate all three chomping
choices. Multiline scalars have the shortest witness and one extra content
line. Plain continuations use the same payload on each continuation.
The escape-name table includes all YAML escapes supported by the written
reader contract and Unicode scalar/control boundaries. Lone surrogates and
out-of-range escapes are excluded. Canonical decimal integers are the only
plain values converted to integers. Boolean and null-like words remain
strings; an empty value is null.

## Exclusion registry

Every derivation is crossed with every applicable rule. Edits are single
insertions, replacements or deletions; their identity includes the original
derivation. Applicability is determined by syntax metadata, never a parser.

| Rule | Applicability and edit |
| --- | --- |
| duplicate-key | Root mapping: append its first key again |
| bad-indentation | Any document: insert a tab before its first token |
| missing-delimiter | Flow collection: delete its outermost closing delimiter |
| invalid-escape | Any quoted scalar: replace it with a double-quoted invalid escape |
| unterminated-quote | Any quoted scalar: remove its closing quote |
| tag | Any scalar: prefix an explicit tag |
| anchor | Any scalar: prefix an anchor |
| alias | Any scalar: replace it with an undefined alias |
| merge-key | Root mapping: insert a merge-key member |
| directive | Any document: prepend a YAML directive and document marker |
| multiple-documents | Any document: append a document marker and second mapping |
| multiline-quote | Any quoted scalar: insert a physical newline inside its quotes |
| indentation-indicator | Any block scalar: add an explicit indentation indicator |

The oracle records whether each neighbor is valid general YAML or invalid
YAML syntax. Expected dialect refusal comes from this registry, not the
external parser. The raw composition tree preserves ordered key/value pairs,
scalar tag, spelling, style and source marks before normalization. Duplicate
keys are detected before converting pairs to a dictionary. The adapter uses
style and spelling instead of YAML 1.1 implicit tags. Parser exceptions from
invalid syntax are observations; unexpected exceptions and broken imports
are `oracle_error`. Only absence of the top-level `yaml` module is
`oracle_unavailable`. Neither means agreement.

## Qualification and limits

`python3 scripts/fixtures/grammar_cases.py --inventory` regenerates a streaming
inventory. It prints counts and a SHA-256 digest; `--output PATH` retains the
full derivation inventory outside the repository. The gate starts with this
inventory and checks equality against an independent combinatorial count.
It then observes the same cases with PyYAML and records disagreements in full.
The default work budget stops an incomplete qualification explicitly at 60
seconds. `--seconds 0` requests an unlimited run. A stopped run is red, with
actual processed counts and unobserved counts; it is never a smaller passing
domain. This budget is an operational stop, not a grammar bound.

The mutation harness uses a separately named control domain to finish every
assertion under each mutation. That control proves the assertions have teeth;
it does not qualify the baseline language. Full qualification is required to
close the specification. Missing PyYAML leaves generation and refusal checks
active and emits a named stand-down for reader and policy observations.
