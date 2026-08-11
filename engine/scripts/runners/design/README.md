# Veldo design runners (reference)

The two mechanical ends of the design contract.

## token_lint.py - the token layer

Screens are built from named design tokens, not raw values, so a screen is
on-design by construction. This linter fails a file that hardcodes a color or
a spacing value the token set already names.

```
token_lint.py <tokens.json> <file> [file ...]     # exit 1 on violations
```

`tokens.json` declares the token sets and an `allow_raw` list of literals that
are legitimate (0, 1px borders, 100%, transparent). A raw hex/rgb color or a
px value not in `allow_raw` is drift. The `fixtures/` pair shows both outcomes:
`good.css` (all tokens, clean) and `bad.css` (raw hex, rgba, and px, six
violations).

## baseline_compare.py - the visual-fidelity layer

A human approves a rendered state against its design ONCE; that render becomes
a stored baseline; the machine then guards drift forever. This compares a
current render to its baseline and passes only if the fraction of differing
pixels is within a declared tolerance. It is never a machine-diff of a render
against a design export (unclosable); always render-vs-approved-baseline.

```
baseline_compare.py <baseline.png> <current.png> [--config c.json] [--name n]
```

`--config` sets `default_tolerance` and per-baseline tolerances; `--name`
selects one. A dimension mismatch is an automatic failure - the layout moved.
Requires Pillow (PIL).

## Why these are mechanical here

Both are pure Python (token lint) and Pillow (baseline compare), so this
repository's gate exercises them in its unit self-test. A consuming repo
points the gate's `token_lint` and `visual_baselines` slots at its own tokens,
sources, and approved baselines. The design VERDICT (a human approving a
render as the baseline) is the separate human review lane; these tools guard
what that verdict locked in.
