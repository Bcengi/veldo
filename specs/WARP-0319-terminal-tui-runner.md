---
schema: veldo.spec/v1
id: WARP-0319
title: Terminal/TUI runner (reference) - B19 of PLAN-0003
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0003
work: B19
plan_revision: 2
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A terminal/TUI runner ships at
      engine/scripts/runners/terminal/terminal_runner.py. It reads a
      journey (a single JSON object naming a command argv, keystrokes to feed,
      the terminal rows and cols, an optional timeout, and a list of assertions),
      drives the command in a REAL pseudo-terminal via the standard-library pty
      module, feeds the declared keystrokes to its stdin, and renders the emitted
      bytes through a REAL VT/ANSI renderer into a screen model (a grid of cells
      each carrying a char and attributes, a cursor, current SGR state, and a
      scrollback history). The renderer is a pure function of its input with no
      I/O and handles the common sequences a TUI emits: cursor position (CUP) and
      relative cursor moves, erase in display and erase in line, SGR (bold, dim,
      underline, reverse, the eight standard and eight bright colors, and reset),
      carriage return, line feed with scroll into history, backspace, and tab;
      an unknown sequence is consumed and ignored rather than printed as text.
  - id: AC2
    text: The assertion kinds address the rendered screen model with zero-based
      row and column coordinates. cell asserts a single cell's char and/or a
      non-empty attrs map, text_at asserts a run of text at a position,
      history_contains asserts a substring on some scrollback line that scrolled
      off the top, and attr asserts one cell's attributes only. A cell/text/attr
      mismatch fails loud naming the coordinate and expected-versus-got. A
      cell or attr assertion that observes nothing (no char and no attrs, or no
      named attribute), an empty text, an unknown kind, and a journey that
      declares no assertions are all named errors, never a silent pass, so a
      journey can never rubber-stamp.
  - id: AC3
    text: The passing fixture
      (engine/scripts/runners/terminal/fixtures/pass.terminal.json)
      exits 0. It is a well-formed journey driving a small deterministic terminal
      program that reads one keystroke line, scrolls eight lines through a
      six-row screen so the first lines land in scrollback, then clears the screen
      and places a bold red ERR at row 3 col 5 (one-based in the stream) and a
      status line echoing the keystroke; every cell, attribute, and scrollback
      line matches its assertion, so terminal_runner.py on that fixture exits 0.
  - id: AC4
    text: The deliberately-failing fixture
      (engine/scripts/runners/terminal/fixtures/fail.terminal.json)
      exits 1 with the failure named. It drives the same program except the
      program DROPS the bold attribute and renders plain red ERR instead of bold
      red; layout, scrollback, and the status line stay correct, so only the
      dropped-attribute assertions fail and the runner exits 1 printing the cell
      coordinate and expected-versus-got. This is a real defect a raw-byte grep
      for the text ERR would never catch, which is why the runner models the
      screen rather than the byte stream. The defect is deterministic and
      timing-independent.
  - id: AC5
    text: The assertions reflect real observed behavior and the renderer control
      logic is unit-tested in scripts/selftest.py over CRAFTED byte strings with
      no pseudo-terminal (cursor positioning, SGR bold/color and reset, CR/LF,
      line wrap, scroll into history, and erase), and the assertion grading is
      shown to name a wrong char, a wrong attribute, a text and a history miss, an
      out-of-bounds coordinate, an unknown kind, and a vacuous assertion. Because
      the stdlib pty works deterministically on this Linux box, both shipped
      fixtures are also driven end to end through a REAL pty (pass -> exit 0,
      fail -> exit 1 with the dropped bold attribute named at its cell). All prior
      selftest cases keep passing and the gate stays green.
  - id: AC6
    text: The runner is generic - zero company or product names in the runner,
      fixtures, wrapper, or README - and .veldo/capabilities.yaml (template and
      repository instance, kept byte-identical) declares it status mechanical: the
      renderer is a pure function gate-tested over crafted byte strings and both
      fixtures are driven end to end through a real pty in the gate on this
      stdlib-only Linux box, so both the control logic and its real surface run in
      the gate here. The live drive is POSIX-only and fails loud where no pty
      exists. The docs-hygiene, secret, lint, and template-sync gates stay green.
required_evidence: [unit, operational]
rollback: git revert; B19 adds a new runner file, a fixture pair, a wrapper and a
  README under engine, a selftest block, and an honest capabilities
  entry (template and instance) - no protected gate script or enforcer is touched,
  so reverting removes the reference artifact and its unit block with no effect on
  any running gate; the prior selftest cases are unchanged.
---

## Intent

PLAN-0003 (the batteries) ships a reference runner for every common product
surface. B19 is the terminal surface. The outcome that should become true is that
a repository can drive its terminal program or TUI with real keystrokes and get
proof of what actually rendered: a character at a cell, an attribute on a cell,
a run of text at a position, and the scrollback history. A TUI that renders to the
wrong cell, drops an attribute, or mismanages scrollback is invisible to a test
that only greps the raw byte stream, because the same visible screen can be
produced by many byte streams and a wrong stream can still contain the right
substring. This runner builds the screen the terminal would actually show and
asserts against that model, so a misplaced cell or a dropped attribute fails the
run naming the row, the column, and expected-versus-got.

## Context

B19 of PLAN-0003, feature F3 (client surfaces: iOS mobile and terminal/TUI), pulled
against plan revision 2, with no dependency. It follows the shipped runners'
pattern: a generic reference under engine/scripts/runners/, a fixture
PAIR (a well-formed passing journey and a deliberately-defective failing journey),
a wrapper, a README, and a unit block that gate-tests the control logic. The
renderer is a stdlib VT/ANSI parser maintaining a grid of cells with attributes, a
cursor, and scrollback; the live drive runs the command in a real pseudo-terminal
via the stdlib pty module, put in raw mode so the renderer sees exactly the bytes
the program wrote (no echo of the fed keystrokes, no newline translation). The
assertion kinds (cell, text_at, attr, history_contains) address the rendered model
with zero-based coordinates so a repo asserts what a user would see.

## Out of scope

The full VT100/VT220 command set: alternate screen buffers, tab-stop programming,
scroll regions (DECSTBM), origin mode, character sets, and 256-color or truecolor
SGR are not modeled; an adopting repo that needs them extends the renderer. The
live drive feeds all keystrokes up front and then drains output, which suits a
deterministic non-interactive-heavy TUI; a richly interactive program that
interleaves reads and writes is served by extending the driver to feed keystrokes
on a separate thread. This spec adds no enforcer and touches no protected path.

## Notes

Why mechanical (not reference): the task's honest-status rule is that a capability
is mechanical when both its control logic AND its real surface run in the gate on
this box via stdlib. The renderer is a pure function gate-tested over crafted byte
strings with no pseudo-terminal, and because the stdlib pty works deterministically
on this Linux box the two shipped fixtures are also driven end to end through a
real pty in the gate; nothing requires a surface this box lacks. The live drive is
POSIX-only and fails loud where no pty exists. required_evidence is [unit,
operational]: unit is the selftest control-logic block (the renderer over crafted
bytes plus the assertion grading), operational is the two shipped fixtures driven
end to end through a real pty via test_terminal_runner.sh (pass -> exit 0, fail ->
exit 1 with the dropped bold attribute named). This remains a shipped reference an
adopting repo wires to its own TUI and the terminal gate slot; the veldo home repo
ships no terminal program of its own to run.

The adversarial properties a reviewer should confirm by rerunning the selftest and
driving the fixtures: (1) the renderer places a glyph at the addressed zero-based
cell, carries SGR bold and color onto written cells and clears them on reset,
treats CR as column zero and LF as a line feed with a scroll into history at the
bottom, wraps a glyph past the last column, and keeps scrollback across an
erase-display; (2) a wrong char, a wrong attribute, a text mismatch, a
history miss, and an out-of-bounds coordinate are each named failures; (3) a
journey that declares no assertions and a cell or attr assertion that observes
nothing are named errors, never a vacuous pass; (4) the passing fixture renders
the bold red ERR at the expected cell, echoes the keystroke into the status line,
and lands the early lines in scrollback (exit 0), while the defective fixture that
drops the bold attribute fails naming the cell (exit 1), a defect a raw-byte grep
would miss.
