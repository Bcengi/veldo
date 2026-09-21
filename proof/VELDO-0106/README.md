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

The one call site reads the policy with `read_policy`, which already handled every shape this file
takes and which VELDO-0104's suite already tests. It is not a second parser written here. The
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

Four rows in `scripts/suites/45_veldo_0106_policyread.py`. The policy is a REAL FILE in each of the
six shapes it can take, in a real git repository with a trunk, a tag and a committed proof bundle,
read through the real call site rather than a hand-built dictionary. The general parser's answer is
computed beside the reader's on the same text, so a row fails if the call site is ever pointed back
at it.

Each of the three declared falsifiers was driven TWICE. Once inside the suite, against copies: the
call site on the general parser, the shape gate removed, the shared parser stripping comments. And
once against the repository's own files, which is the check on the check:

| falsifier | mutation to the repository's own file | result |
|---|---|---|
| AC1 | `_strip_comment` returns the line unchanged | AC1 red, 3 of 4 rows pass |
| AC2 | `_FULL_COMMIT_ID` becomes `re.compile(r".*")` | AC2 red, 3 of 4 rows pass |
| AC3 | `_scalar` in `validate.py` strips a trailing comment | AC3 red, and AC1 red with it, 2 of 4 rows pass |

The fourth row is the negative control: a copy of the organ carrying only an added comment, required
to agree with the original on every case the other rows turn on, so the difference each driven mutant
shows is the mutation and not the copying.

What this is NOT. It is not evidence that the two settings are read correctly everywhere. The
repository has other readers of `.veldo/policy.yaml` and consolidating them is not this item; this
item makes the two settings that gate a landing read correctly at the one call site that gates it.
