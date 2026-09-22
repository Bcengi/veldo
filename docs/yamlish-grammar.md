# Shared document reader grammar

Revision: `veldo.yamlish-grammar/2`. This fixture contract is independent of
the implementation. `scripts/fixtures/yamlish_grammar.json` versions the
production graph, lexical alternatives and exclusion predicates. No
production module imports the fixture.

## Productions and lexical alternatives

The executable grammar is normalized to concrete syntax productions. The
`coverage.productions` table is authoritative for direct child relations.
Abstract EBNF helpers such as value, inline, member, pair and scalar are
inlined into their owning productions; they are not additional counted
productions. Repetition is an arity alternative, not an extra tree node.
The written reader contract is reconciled as follows:

| Written syntax | Concrete productions and alternatives |
| --- | --- |
| Document and optional byte-order mark | document, bom; block map or sequence roots |
| Indented maps and sequences | block-map, block-sequence; one or two children |
| Inline map in a sequence item | compact-map; one or two members |
| Flow collections | flow-map, flow-sequence; empty, one or two children |
| Trailing flow comma | flow-map-trailing, flow-sequence-trailing; one or two children |
| Wrapped flow collections | wrapped-map, wrapped-sequence; empty, one or two children |
| Empty and plain scalars | empty, plain; canonical integers and retained spellings |
| Quoted scalars | single, double; doubled apostrophes and escaped characters |
| YAML escapes | escape; every name in the escape table |
| Literal/folded blocks | literal, folded; clip/strip/keep, one/two content lines |
| Plain continuation | continuation; one/two additional lines |
| Identifier/path keys | key-plain; every identifier/path representative |
| Quoted keys | key-single, key-double; every quoted representative |

Block collections and compact maps accept scalars, nested block collections
and flow collections; block sequences also accept compact maps. Flow and
wrapped collections accept nested flow/wrapped collections and inline
scalars. Empty scalar values occur in mappings, not flow sequences.
Mapping key slots use the three key productions. Document and BOM root
slots accept block collections. These rules are explicitly enumerated in
the versioned graph, including recursive self-pairs.

The scalar alternatives retain all words of length zero through two over
the six-character alphabet and all named integer, leading-zero, boolean,
null-like, Unicode and control partitions. Duplicate payloads retain
separate lexical identities. Each supported style/payload/escape/chomping/
continuation combination is a lexical alternative. Keys retain identifier,
path, single-quoted and double-quoted representatives. Mapping witnesses
use distinct decoded keys. Indentation (one/two spaces), newline (LF/CRLF)
and absent/present trailing comments each receive witnesses. They are not
crossed with every derivation. Comments attach to syntax headers and every
document has a final newline.

Plain words are nonempty and trimmed, do not start with YAML indicators,
and contain neither whitespace followed by `#` nor a colon followed by
whitespace or end of word. Flow words also exclude flow punctuation. Single
quotes double apostrophes. Double quotes escape quotes, backslashes and
controls; non-BMP characters use a single YAML Unicode escape. Literal and
folded payloads retain their spelling. Plain continuations repeat their
payload. The escape table includes Unicode scalar/control boundaries but
no surrogate or out-of-range escapes. Canonical decimal integers alone
become integers; boolean and null-like words stay strings; empty values
are null. The inherited lexical registry permits literal DEL in plain and
continuation styles; PyYAML reports these three witnesses as invalid YAML.
That discrepancy is recorded, not removed after observing parser answers.

## Complete coverage targets

The qualification domain has three criteria, each required in full:

1. Every concrete production and lexical alternative has a witness.
2. Every directly allowed parent/child pair has a witness (k-path, k = 2).
3. Every exclusion rule has a local edit at each applicable production site.

A production site is `(parent, slot, child)`, with a separate document-root
site. Slots distinguish keys from values and document roots. Repeated and
recursive occurrences share their grammar site. Coverage is finite because
it ranges over the grammar graph, not every possible recursive context.

The fixture enumerates required target identities from the grammar,
constructs terminating witnesses and embeds them through shortest legal
root paths. It collects production, lexical and edge coverage from the
emitted derivation trees. Boundary edits use exact spans of the targeted
production occurrence, including nested collections and quoted keys.
A separate arithmetic counter counts lexical partitions, incoming graph
edges and predicate intersections without invoking witness construction,
rendering or target enumeration. Enumerated and witnessed inventories must
both equal it; missing or unexpected identities fail their named row.

The current inventory is 22 productions, 934 lexical alternatives, 132
parent/child pairs and 457 boundary rule/site targets. It produces 1,088
accepted witnesses and 457 boundary inputs. Duplicate-byte witnesses stay
separate. These numbers describe this revision, not an unbounded language
or all combinations of lexical choices, siblings, formatting and nesting.

## Exclusion registry

Applicability is determined by production features in the grammar, never
by parser acceptance. Each edit changes one targeted occurrence.

| Rule | Applicable production and local edit |
| --- | --- |
| duplicate-key | Any mapping: append its first key again |
| bad-indentation | Block collection, compact map, block scalar or continuation: insert a tab in physical indentation |
| missing-delimiter | Flow/wrapped collection: remove its closing delimiter |
| invalid-escape | Quoted scalar or key: replace with an invalid double-quoted escape |
| unterminated-quote | Quoted scalar or key: remove its closing quote |
| tag | Scalar or key: prefix an explicit tag |
| anchor | Scalar or key: prefix an anchor |
| alias | Scalar or key: replace with an undefined alias |
| merge-key | Any mapping: append a merge-key member |
| directive | Document root: prepend a directive and document marker |
| multiple-documents | Document root: append a marker and second document |
| multiline-quote | Quoted scalar or key: insert a physical newline inside quotes |
| indentation-indicator | Literal/folded scalar: insert an explicit indentation indicator |

Boundary witnesses use canonical key `a`, so duplicate-key edits repeat
that actual key. The original bytes, rule and production site are retained.
The oracle classifies neighbors as valid general YAML or invalid YAML;
expected dialect refusal comes from this registry. Reader disagreements
are evidence for a separate consumer task, not a reason to alter targets.

## Oracle and qualification

The oracle uses PyYAML composition, preserving source locations, style,
spelling, node pairs and parser errors before adaptation. Duplicate keys
are detected before dictionary conversion. The dialect adapter uses style
and spelling instead of YAML 1.1 implicit tags. Unexpected exceptions or
broken imports are `oracle_error`; only absence of the top-level `yaml`
module is `oracle_unavailable`. Neither means agreement.

`python3 scripts/fixtures/grammar_cases.py --count` prints the independently
counted target inventory. `--inventory --output PATH` emits all inputs and
reports coverage and its digest. Raw observations can be regenerated with
`python3 scripts/fixtures/yaml_oracle.py --inventory PATH --output RAW_PATH`.
Generation uses only the standard library. The gate observes the complete
inventory; absent PyYAML leaves generation and reader execution active and
prints named stand-downs for reader and policy observations. Installed
oracle errors fail qualification.

The same complete coverage domain runs under mutations and their unmutated
controls. Each mutation must fail its named assertion in a completed run;
a crash, missing assertion or timeout is not detection. Measurement precedes
changes to qualification rows; exceeding 60 added gate seconds requires an
explicit cost stop rather than deleting targets.

## History

Revision 1 exhaustively expanded the three-node bounded domain. It measured
510,928,488 derivations and 5,013,490,520 boundary edits and exceeded the
operational budget. Revision 2 replaces that product with complete grammar
coverage criteria. Historical enumeration remains opt-in through
`--legacy-exhaustive`; `--control` reproduces its diagnostic control domain.
Neither is the current qualification domain.
