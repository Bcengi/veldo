# Veldo terminal / TUI runner (reference)

A generic runner for the terminal surface: it drives a REAL terminal program in a
pseudo-terminal, feeds it declared keystrokes, and renders its byte output through
a REAL VT/ANSI renderer, then asserts what actually landed on the screen: a
character at a row and column, the attributes on a cell (bold, underline,
foreground color, and the like), a run of text at a position, and the scrollback
history that scrolled off the top. A TUI that renders to the wrong cell, drops an
attribute, or mismanages scrollback is invisible to a test that only greps the raw
byte stream, because the same visible screen can be produced by many byte streams
and a wrong stream can still contain the right substring. This runner builds the
screen the terminal would actually show and asserts against that model. It uses
only the Python standard library.

## Use

```
terminal_runner.py <journey.json>     # exit 0 = every assertion held
test_terminal_runner.sh               # self-contained regression
```

## Journey format

A journey is a single JSON object naming the command, the keystrokes to feed, the
terminal size, and the assertions:

```json
{
  "name": "status line renders bold error at row 3",
  "command": ["python3", "-c", "..."],
  "keystrokes": ["OK\n"],
  "rows": 6,
  "cols": 40,
  "timeout": 5,
  "assertions": [
    {"kind": "cell", "row": 2, "col": 4, "char": "E",
     "attrs": {"bold": true, "fg": "red"}},
    {"kind": "text_at", "row": 4, "col": 0, "text": "status: OK"},
    {"kind": "attr", "row": 2, "col": 6, "bold": true, "fg": "red"},
    {"kind": "history_contains", "text": "row 1"}
  ]
}
```

All row and column coordinates in assertions are ZERO-BASED grid indices (row 0 is
the top line, col 0 the leftmost column). The ANSI cursor-position sequences the
program emits are one-based in the byte stream, as the terminal convention has it,
but assertions address the rendered model, which is zero-based.

### Assertion kinds

- `cell` a single grid cell. `char` (optional) is the exact character and `attrs`
  (optional) is a map of attribute name to expected value. At least one of `char`
  or a non-empty `attrs` must be present, or the assertion observes nothing and is
  a journey error.
- `text_at` a run of text starting at `(row, col)` read left to right. `text` must
  be non-empty.
- `attr` one cell's attributes only. Every key other than `kind`, `row`, and `col`
  is an attribute with its expected value; at least one attribute is required.
- `history_contains` a substring that must appear on some scrollback line (a line
  that scrolled off the top). This is the assertion a raw-byte grep cannot make,
  because scrollback is a property of the rendered model.

A journey with no assertions asserts nothing and is a named journey error, never a
silent pass.

Recognized attribute names: `bold`, `dim`, `underline`, `reverse` (booleans) and
`fg`, `bg` (a color name from the eight standard colors, optionally prefixed
`bright_`, or `null` for the terminal default).

Exit 0 = every assertion held. Exit 1 = at least one assertion failed (each
failure names the coordinate and expected-versus-got) or the journey was
malformed. Exit 2 = usage error.

## The renderer

The renderer parses a byte stream into a grid of cells, a cursor, current SGR
state, and a scrollback list. It handles the common sequences a TUI emits: cursor
position (CUP `H`/`f`), relative moves (`A`/`B`/`C`/`D`/`G`/`d`), erase in display
(`J`) and erase in line (`K`), SGR (`m`: bold, dim, underline, reverse, the eight
standard and eight bright colors, and reset), carriage return, line feed with
scroll into history, backspace, tab, and scroll up (`S`). Unknown sequences are
consumed and ignored rather than printed as text, so an unhandled escape never
corrupts the grid.

## Fixtures

`fixtures/pass.terminal.json` is a well-formed journey: a small deterministic TUI
reads one keystroke line, scrolls eight lines through a six-row screen so the
first lines land in scrollback, then clears the screen and places a bold red
`ERR` at row 3 col 5 (one-based in the stream) and a status line echoing the
keystroke. Every cell, attribute, and scrollback line matches, so the runner
exits 0.

`fixtures/fail.terminal.json` is the deliberately-defective journey: the same TUI
except it DROPS the bold attribute and renders plain red `ERR` instead of bold
red. Layout, scrollback, and the status line are all still correct, so only the
dropped-attribute assertions fail; the runner exits 1 naming the cell coordinate
and expected-versus-got. A byte-stream grep for `ERR` would never catch this
defect, which is exactly why the runner models the screen.

```
terminal_runner.py fixtures/pass.terminal.json     # exit 0
terminal_runner.py fixtures/fail.terminal.json     # exit 1
```

## Out of scope

The renderer covers the common sequences a line-of-business TUI emits, not the
full VT100/VT220 command set: alternate screen buffers, tab-stop programming,
scroll regions (DECSTBM), origin mode, character sets, and 256-color or truecolor
SGR are not modeled. An adopting repo that needs them extends the renderer. The
live drive feeds all keystrokes up front and then drains output, which suits a
deterministic non-interactive-heavy TUI; a repo with a richly interactive program
that interleaves reads and writes can extend the driver to feed keystrokes on a
separate thread.

## Why this is a reference (status: mechanical)

The renderer (parse a byte stream into a grid, attributes, cursor, and scrollback,
and grade assertions) is a pure function of its input with no I/O, so its control
logic is gate-tested in `scripts/selftest.py` over crafted byte strings with no
pseudo-terminal at all. Because the pty module works deterministically on the
Linux box the gate runs on, the selftest also drives BOTH shipped fixtures through
a real pty end to end (well-formed -> exit 0, defective -> exit 1 with the dropped
attribute named), so the runner's live path is proven in the gate with stdlib
only. The capability is therefore `mechanical`: both the renderer and its real
surface run in the gate here. The live drive is POSIX-only and fails loud on a
platform without a pty. This is still a shipped reference an adopting repo wires to
its own TUI and the terminal gate slot; the veldo home repo ships no terminal
program of its own to run.
