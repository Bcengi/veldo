# Veldo web journey runner (reference)

A real, flow-first web UI runner: it drives a browser (Playwright chromium)
through a journey, asserts behavior at every step, captures named UI states
as screenshots, and runs a dependency-free accessibility scan. The method's
UI-proof hierarchy is flows first, then states, then visual fidelity; this
runner is the flows-and-states layer. Visual fidelity (a rendered state
composited against its design) is `scripts/veldo-visual.py`.

## Why it is a reference

It ships working and self-tested, but a repository wires it to ITS app and
ITS journeys, then points the gate's `journeys` slot at it (see the
`/veldo:plan` regression section for computing the active per-spec suite). A
repository with no user interface leaves the slot na.

## Use

```
run.sh <journey.json> [outdir]        # exit 0 = flow proven and a11y clean
test_web_runner.sh                    # the runner's own regression
```

Requires Node and the `playwright` package with its chromium browser. The
harness resolves Playwright from the global npm root or `NODE_PATH`.

## Journey format

```json
{
  "name": "save a search",
  "file": "app.html",          // resolved next to the journey; or "url": "https://..."
  "viewport": {"width": 1024, "height": 768},
  "a11y": true,
  "a11y_fail_on": true,
  "steps": [
    {"action": "state", "name": "landing"},
    {"action": "fill", "selector": "#q", "value": "lisbon rail"},
    {"action": "click", "selector": "#save"},
    {"action": "expect_visible", "selector": "#status"},
    {"action": "expect_text", "selector": "#status", "text": "Saved"},
    {"action": "state", "name": "after-save"}
  ]
}
```

Actions: `goto`, `click`, `fill`, `wait`, `expect_visible`, `expect_hidden`,
`expect_text`, `state` (screenshot). A failed assertion stops the journey,
captures a `FAILURE-step-N.png`, and exits 1: a flow that cannot complete is
unproven from that point, and perfect screenshots of a broken flow are not
evidence. The a11y scan flags missing image alt text, unlabeled inputs,
controls with no accessible name, a missing document language, and duplicate
ids; with `a11y_fail_on` the violations fail the run.

The `fixtures/` pair demonstrates both outcomes: `pass.journey.json` (green,
states captured, a11y clean) and `fail.journey.json` against `broken.html`
(the flow assertion and four a11y rules both fire).
