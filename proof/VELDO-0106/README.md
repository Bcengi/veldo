# VELDO-0106 proof

PLAN-0020 W6. Author: Ava (Claude), under Dmitry's rule that when Codex is out the author writes and
Codex validates; an unbriefed Codex review was run over this work before it landed.

## Why this item exists

VELDO-0105 shipped the start line and the owner armed the rule. An adversarial read of that landing
then asked a question nobody had asked: what does the code actually do with the file the owner writes?

Three answers, all wrong, all silent.

A trailing comment on the flag turned it off. `required: true  # armed by the owner` read as **false**,
because the general front-matter parser strips a whole-line comment and not a trailing one. The rule
the owner had just armed returned to advisory with no error anywhere, and every problem it would have
refused printed as a warning instead. That is the worst shape a defect can have: nothing fails.

On the inline form the same comment lost the start line as well, so the rule would have judged the
entire corpus.

And `from_commit: 0123456` came back as `123456`. The parser coerces a digit-only value to an integer,
the leading zero goes, and the line silently names a different commit.

## What landed

The one call site reads the policy with `read_policy`, which handled the regression examples and which VELDO-0104's suite already tests. It is not a second parser written here. The
validator still hands in its general parser and that parser is still used for the spec front matter
beside it, which is what it is for.

A recorded start line must now be forty hexadecimal characters, refused **by shape** before anything is
resolved, and the refusal names the value it was given. A branch or a tag resolves today and to
something else tomorrow, and the ref namespace is not a protected path, so the owner's line could
move without the owner. An abbreviation becomes ambiguous as history grows. A leading-zero value is
the coercion showing through. Refused is IN SCOPE, so a mistyped line exempts nothing, which is the
same fail-closed direction VELDO-0105 chose for an unresolvable line.

## What was deliberately not done, and the measurement that says why

The obvious repair is to teach the general parser to strip trailing comments. It is what YAML does,
it is what this module's own reader already does, and the repository has a `reuse_one_parser` pattern
that argues for it.

It was measured before it was attempted. **55 of this repository's 328 specifications and plans parse
differently under that change**, 49 of them in `acceptance_criteria` text and the rest in `risk`,
`constraints` and `status` fields containing a hash. It would silently truncate the text of
specifications that have already shipped, to fix a flag nobody had yet tripped, and the gate would go
green on it because nothing compares a specification's text across a parser change.

That measurement is AC3. It runs over the real corpus on every run and prints the count rather than
pinning it, so a later reader who wants to make the change sees what it costs first.

## What the evidence is, and what it is not

Six rows in `scripts/suites/45_veldo_0106_policyread.py`. The policy is a REAL FILE in each of the
seventeen regression examples, in a real git repository with a trunk, a tag and a committed proof bundle,
read through the real call site rather than a hand-built dictionary. The general parser's answer is
computed beside the reader's on the same text, so a row fails if the call site is ever pointed back
at it.

Each declared falsifier is driven twice: inside the suite against copies, and once against the
repository's own files, which is the check on the check. Three of the seven external drives rebuild
the EXACT pre-fix code of a demonstrated bypass rather than something adjacent to it:

| falsifier | mutation to the repository's own file | result |
|---|---|---|
| AC1, pre-fix | `_scan_scalar` enters quote mode at a quote anywhere, not at the scalar's first character | AC1 and the oracle red |
| AC1, pre-fix | `_policy_lines` back to `str.splitlines()` | AC1 and the oracle red |
| AC1, pre-fix | `_root_keys` treats every key as top level | AC1 and the oracle red |
| AC1 | the file decoded as `utf-8` rather than `utf-8-sig` | AC1 and the oracle red |
| AC2 | `_FULL_COMMIT_ID` becomes `re.compile(r".*")` | AC2 red |
| AC3 | `_scalar` in `validate.py` strips a trailing comment | AC3 red |
| AC4 | `read_policy` catches its own refusal and answers with an empty policy | AC4 red |

The sixth row is the negative control: a copy of the organ carrying only an added comment, required
to agree with the original on every case the other rows turn on.

## Three reviews, eleven bypasses, and why the reader was rebuilt

The gate was GREEN at `d1809f1` and again at `2e57500`, and the suite passed at both, while eleven
demonstrated bypasses were live across them.

An unbriefed Codex review found two. A review briefed at that class found eight more. A third, told
nothing about where to look, found three, and **two of those three were regressions introduced by the
fix for the first two**: the quote-aware comma split written to stop `{required: true, note: "leave
this, required: false"}` broke `{note: don't relax, required: true}`, which the version before it had
parsed correctly.

The eleven are one defect wearing eleven hats. A byte order mark. A space before the colon. An
apostrophe or an inch mark in a plain value. A backslash-escaped quote. A U+2028 inside a note. A
nested `{}` or `[]`. The key written as prose inside another key's block scalar. The key nested under
an unrelated mapping. The key twice. A member whose value sits on the next line. Every one parsed to
something non-empty and wrong, so the rule read as off and nothing failed anywhere.

The worst did not disarm the flag at all. It moved the start line forward to a later commit, which
silently exempts every bundle between the two and prints as a tidy "not applicable".

A subset reader cannot be patched into a YAML reader. Each patch closed the shape it was shown and
left the next one, and twice it opened one. So the reader was rebuilt around a contract it can hold:
**return exactly what the owner wrote, or refuse.**

AC4 is the gap underneath all eleven. The reader had one way of saying "no settings" and it meant
two different things: a repository that never adopted the rule, and a setting the owner wrote that
could not be parsed. The first is properly advisory. The second must never be. It now has three
answers and no fourth.

## The oracle

AC1's shape list is checked against a real YAML parser, not only against itself, because the lesson
of eleven bypasses is that a list of shapes the author thought of is not a domain: every one of the
eleven was a shape nobody had listed. PyYAML is not a dependency of the shipped reader, which is
standard library only, so that row stands down by name where PyYAML is absent. One divergence is
excluded by name and with its reason: YAML 1.1 reads a leading-zero digit string as octal, and
keeping that value a string is the defect AC2 exists to prevent, so agreeing there would be wrong.

The independent oracle receives those same seventeen inputs; agreement adds no coverage and
does not establish completeness. AC4 likewise exercises selected refusals, not every input outside
the accepted syntax. The accepted syntax and its boundaries are written in
[the strict shared reader's grammar](../../.veldo/yamlish.py), introduced by VELDO-0110;
policy-specific checks live in read_policy. Exhaustive accepted/refused input coverage is
INTENDED and NOT YET DEMONSTRATED by these rows.

Historical scope at this item's landing follows; VELDO-0110 subsequently consolidated the readers.
It is not evidence that the two settings are read correctly everywhere. The
repository has other readers of `.veldo/policy.yaml` and consolidating them is not this item; this
item makes the two settings that gate a landing read correctly at the one call site that gates it.
