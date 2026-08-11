#!/usr/bin/env python3
"""VELDO terminal / TUI runner (reference).

Drives a REAL terminal program, feeds it declared keystrokes, and renders its
byte output through a REAL VT/ANSI renderer, then asserts what actually landed on
the screen: a character at a row and column, the attributes on a cell (bold,
underline, foreground color, and the like), a run of text at a position, and the
scrollback history that scrolled off the top. A TUI that renders to the wrong
cell, drops an attribute, or mismanages scrollback is invisible to a test that
only greps the raw byte stream, because the same visible screen can be produced
by many different byte streams and a wrong stream can still contain the right
substring. This runner builds the screen the terminal would actually show and
asserts against that model, so a misplaced cell or a dropped attribute fails the
run naming the row, the column, and expected-versus-got.

  terminal_runner.py <journey.json>

The renderer (parse a byte stream into a grid of cells with attributes, a cursor,
and scrollback) is a pure function of its input with no I/O, so its control logic
is gate-tested over crafted byte strings with no pseudo-terminal at all. The live
drive runs the command in a real pseudo-terminal via the standard-library pty
module, which is POSIX-only: on a platform without pty the live drive fails loud
rather than pretending to have driven a terminal.

Journey format (a single JSON object):

  {
    "name": "status line renders bold error at row 3",
    "command": ["python3", "-c", "..."],   # argv, run in a real pty (no shell)
    "keystrokes": ["OK\n"],                 # bytes fed to the program's stdin
    "rows": 6,                              # terminal height
    "cols": 40,                             # terminal width
    "timeout": 5,                           # seconds to wait for the program
    "assertions": [
      {"kind": "cell", "row": 2, "col": 4, "char": "E",
       "attrs": {"bold": true, "fg": "red"}},
      {"kind": "text_at", "row": 4, "col": 0, "text": "status: OK"},
      {"kind": "attr", "row": 2, "col": 6, "bold": true, "fg": "red"},
      {"kind": "history_contains", "text": "row 1"}
    ]
  }

All row and column coordinates in assertions are ZERO-BASED grid indices (row 0 is
the top line, col 0 the leftmost column). The ANSI cursor-position sequences the
program emits are one-based in the byte stream, as the terminal convention has it,
but the assertions address the rendered model, which is zero-based.

Assertion kinds:

  cell             a single grid cell. "char" (optional) is the exact character
                   and "attrs" (optional) is a map of attribute name to expected
                   value; at least one of "char" or a non-empty "attrs" must be
                   present or the assertion observes nothing and is a journey
                   error (a cell assertion that checks neither the glyph nor an
                   attribute would pass against any screen).
  text_at          a run of text starting at (row, col) read left to right across
                   the cells. "text" must be a non-empty string.
  attr             one cell's attributes only. Every key other than kind, row,
                   and col is an attribute (bold, dim, underline, reverse, fg,
                   bg) with its expected value; at least one attribute is
                   required or the assertion observes nothing and is a journey
                   error.
  history_contains a substring that must appear on some line of the scrollback
                   history (a line that scrolled off the top). "text" must be a
                   non-empty string. This is the assertion a raw-byte grep cannot
                   make, because scrollback is a property of the rendered model.

A journey with no assertions asserts nothing and is a named journey error, never
a silent pass: a runner that could only ever say PASS is worse than none.

Exit 0 = every assertion held against the rendered screen. Exit 1 = at least one
assertion failed (each failure names the coordinate and expected-versus-got) or
the journey was malformed. Exit 2 = usage error.

The recognized attribute names are bold, dim, underline, reverse (booleans) and
fg, bg (a color name from the eight standard colors, optionally prefixed
bright_, or null for the terminal default). The renderer handles the common
sequences a TUI emits: cursor position (CUP), relative cursor moves, erase in
display and erase in line, SGR (bold, dim, underline, reverse, the eight standard
and eight bright colors, and reset), carriage return, line feed with scroll,
backspace, and tab. Unknown sequences are consumed and ignored rather than
printed as text, so an unhandled escape never corrupts the grid.
"""
import json
import select
import sys
import time
from pathlib import Path


# the terminal model

COLOR_NAMES = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]
ATTR_KEYS = ("bold", "dim", "underline", "reverse", "fg", "bg")


def _blank_attrs():
    return {"bold": False, "dim": False, "underline": False, "reverse": False,
            "fg": None, "bg": None}


class Cell:
    """One screen cell: a character plus its display attributes."""

    __slots__ = ("char", "bold", "dim", "underline", "reverse", "fg", "bg")

    def __init__(self):
        self.char = " "
        self.bold = False
        self.dim = False
        self.underline = False
        self.reverse = False
        self.fg = None
        self.bg = None

    def clear(self):
        self.char = " "
        self.bold = self.dim = self.underline = self.reverse = False
        self.fg = self.bg = None

    def attr(self, key):
        return getattr(self, key)


class Screen:
    """A grid of cells with a cursor, current SGR state, and scrollback history.

    Pure state: fed a byte stream by feed(), never touches the filesystem or the
    network, so it is deterministic and gate-testable with crafted input.
    """

    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.grid = [[Cell() for _ in range(cols)] for _ in range(rows)]
        self.row = 0
        self.col = 0
        self.cur = _blank_attrs()
        self.history = []

    # helpers

    def line_text(self, row):
        return "".join(c.char for c in self.grid[row])

    def text_at(self, row, col, n):
        return "".join(self.grid[row][col + k].char for k in range(n))

    def in_bounds(self, row, col):
        return 0 <= row < self.rows and 0 <= col < self.cols

    # cursor and scroll

    def _clamp(self):
        if self.row < 0:
            self.row = 0
        if self.row >= self.rows:
            self.row = self.rows - 1
        if self.col < 0:
            self.col = 0
        if self.col >= self.cols:
            self.col = self.cols - 1

    def _scroll_up(self):
        self.history.append(self.line_text(0).rstrip())
        self.grid.pop(0)
        self.grid.append([Cell() for _ in range(self.cols)])

    def line_feed(self):
        if self.row >= self.rows - 1:
            self._scroll_up()
        else:
            self.row += 1

    def put(self, ch):
        if self.col >= self.cols:
            self.col = 0
            self.line_feed()
        cell = self.grid[self.row][self.col]
        cell.char = ch
        cell.bold = self.cur["bold"]
        cell.dim = self.cur["dim"]
        cell.underline = self.cur["underline"]
        cell.reverse = self.cur["reverse"]
        cell.fg = self.cur["fg"]
        cell.bg = self.cur["bg"]
        self.col += 1

    # SGR

    def apply_sgr(self, params):
        if not params:
            params = [0]
        for n in params:
            if n == 0:
                self.cur = _blank_attrs()
            elif n == 1:
                self.cur["bold"] = True
            elif n == 2:
                self.cur["dim"] = True
            elif n == 4:
                self.cur["underline"] = True
            elif n == 7:
                self.cur["reverse"] = True
            elif n == 22:
                self.cur["bold"] = False
                self.cur["dim"] = False
            elif n == 24:
                self.cur["underline"] = False
            elif n == 27:
                self.cur["reverse"] = False
            elif 30 <= n <= 37:
                self.cur["fg"] = COLOR_NAMES[n - 30]
            elif n == 39:
                self.cur["fg"] = None
            elif 40 <= n <= 47:
                self.cur["bg"] = COLOR_NAMES[n - 40]
            elif n == 49:
                self.cur["bg"] = None
            elif 90 <= n <= 97:
                self.cur["fg"] = "bright_" + COLOR_NAMES[n - 90]
            elif 100 <= n <= 107:
                self.cur["bg"] = "bright_" + COLOR_NAMES[n - 100]
            # any other code is ignored

    # erase

    def erase_display(self, mode):
        if mode == 2 or mode == 3:
            for r in range(self.rows):
                for c in range(self.cols):
                    self.grid[r][c].clear()
        elif mode == 1:
            for r in range(self.row):
                for c in range(self.cols):
                    self.grid[r][c].clear()
            for c in range(self.col + 1):
                self.grid[self.row][c].clear()
        else:  # mode 0: cursor to end
            for c in range(self.col, self.cols):
                self.grid[self.row][c].clear()
            for r in range(self.row + 1, self.rows):
                for c in range(self.cols):
                    self.grid[r][c].clear()

    def erase_line(self, mode):
        if mode == 2:
            for c in range(self.cols):
                self.grid[self.row][c].clear()
        elif mode == 1:
            for c in range(self.col + 1):
                self.grid[self.row][c].clear()
        else:  # mode 0: cursor to end of line
            for c in range(self.col, self.cols):
                self.grid[self.row][c].clear()

    # CSI dispatch

    def csi(self, params_str, final):
        priv = ""
        if params_str and params_str[0] in "?<>=":
            priv = params_str[0]
            params_str = params_str[1:]
        nums = []
        if params_str:
            for p in params_str.split(";"):
                nums.append(int(p) if p.isdigit() else 0)

        def n0(default=0):
            return nums[0] if nums else default

        if final in ("H", "f"):
            r = (nums[0] if len(nums) >= 1 else 1) - 1
            c = (nums[1] if len(nums) >= 2 else 1) - 1
            self.row, self.col = r, c
            self._clamp()
        elif final == "A":
            self.row -= max(1, n0(1)); self._clamp()
        elif final == "B":
            self.row += max(1, n0(1)); self._clamp()
        elif final == "C":
            self.col += max(1, n0(1)); self._clamp()
        elif final == "D":
            self.col -= max(1, n0(1)); self._clamp()
        elif final == "G":
            self.col = max(1, n0(1)) - 1; self._clamp()
        elif final == "d":
            self.row = max(1, n0(1)) - 1; self._clamp()
        elif final == "J":
            self.erase_display(n0(0))
        elif final == "K":
            self.erase_line(n0(0))
        elif final == "m" and not priv:
            self.apply_sgr(nums)
        elif final == "S":
            for _ in range(max(1, n0(1))):
                self._scroll_up()
        # h, l (mode set/reset), and any other final byte are consumed and ignored


def render(data, rows, cols):
    """Render a byte stream (bytes or str) into a Screen. Pure: no I/O.

    Decoded as latin-1 so every byte maps to exactly one code point and the
    escape parsing is byte-exact; the fixtures are ASCII.
    """
    if isinstance(data, bytes):
        s = data.decode("latin-1")
    else:
        s = data
    scr = Screen(rows, cols)
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch == "\x1b":
            if i + 1 < n and s[i + 1] == "[":
                j = i + 2
                params = ""
                while j < n and s[j] in "0123456789;?<>=":
                    params += s[j]
                    j += 1
                while j < n and 0x20 <= ord(s[j]) <= 0x2F:  # intermediates
                    j += 1
                if j < n:
                    scr.csi(params, s[j])
                    i = j + 1
                    continue
                break  # incomplete CSI at end of stream
            # a non-CSI escape (single-char or two-char): skip the escape and the
            # following byte if present
            i += 2
            continue
        if ch == "\r":
            scr.col = 0
            i += 1
        elif ch == "\n":
            scr.line_feed()
            i += 1
        elif ch == "\b":
            if scr.col > 0:
                scr.col -= 1
            i += 1
        elif ch == "\t":
            scr.col = min(scr.cols - 1, (scr.col // 8 + 1) * 8)
            i += 1
        elif ch == "\x07":  # bell
            i += 1
        elif ord(ch) < 0x20:  # any other control byte: ignore
            i += 1
        else:
            scr.put(ch)
            i += 1
    return scr


# assertions

def validate_journey(journey):
    """Pure structural check. Returns an error string or None.

    A journey that declares no assertions asserts nothing and is a journey error,
    so a runner that could only ever pass is impossible.
    """
    if not isinstance(journey, dict):
        return "journey must be a JSON object"
    cmd = journey.get("command")
    if not isinstance(cmd, list) or not cmd:
        return "journey has no 'command' argv list"
    for k in ("rows", "cols"):
        v = journey.get(k)
        if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
            return f"journey '{k}' must be a positive integer, got {journey.get(k)!r}"
    assertions = journey.get("assertions")
    if not isinstance(assertions, list) or not assertions:
        return (f"journey {journey.get('name')!r} declares no assertions: "
                "a journey that asserts nothing is a journey error, never a pass")
    return None


def _assertion_error(a):
    """Return an error string if the assertion observes nothing or is malformed,
    else None. This is what stops a vacuous assertion from rubber-stamping."""
    kind = a.get("kind")
    if kind == "cell":
        has_char = "char" in a
        has_attrs = isinstance(a.get("attrs"), dict) and len(a["attrs"]) > 0
        if not has_char and not has_attrs:
            return ("cell assertion observes nothing: it must pin 'char' or a "
                    "non-empty 'attrs' map")
        return None
    if kind == "attr":
        keys = [k for k in a if k in ATTR_KEYS]
        if not keys:
            return ("attr assertion observes nothing: name at least one attribute "
                    f"of {list(ATTR_KEYS)}")
        return None
    if kind in ("text_at", "history_contains"):
        if not isinstance(a.get("text"), str) or a.get("text") == "":
            return f"{kind} assertion needs a non-empty 'text'"
        return None
    return f"unknown assertion kind {kind!r}"


def _check_attrs(scr, row, col, expected, label):
    failures = []
    cell = scr.grid[row][col]
    for key, want in expected.items():
        if key not in ATTR_KEYS:
            failures.append(f"{label} ({row},{col}): unknown attribute {key!r}")
            continue
        got = cell.attr(key)
        if got != want:
            failures.append(f"{label} ({row},{col}): expected {key}={want!r}, got {key}={got!r}")
    return failures


def evaluate_assertions(scr, assertions):
    """Grade every assertion against the rendered screen. Pure: no I/O.

    Returns a list of failure strings (empty means every assertion held). A
    malformed or vacuous assertion is itself a named failure, so the runner never
    passes on an assertion that observes nothing.
    """
    failures = []
    for a in assertions:
        err = _assertion_error(a)
        if err:
            failures.append(err)
            continue
        kind = a["kind"]
        if kind == "history_contains":
            text = a["text"]
            if not any(text in line for line in scr.history):
                failures.append(
                    f"history_contains: {text!r} not found in scrollback "
                    f"({len(scr.history)} line(s) scrolled off)")
            continue
        row = a.get("row")
        col = a.get("col")
        if not isinstance(row, int) or not isinstance(col, int):
            failures.append(f"{kind} assertion needs integer 'row' and 'col'")
            continue
        if kind == "text_at":
            text = a["text"]
            if not scr.in_bounds(row, col) or not scr.in_bounds(row, col + len(text) - 1):
                failures.append(
                    f"text_at ({row},{col}): {text!r} runs outside the "
                    f"{scr.rows}x{scr.cols} screen")
                continue
            got = scr.text_at(row, col, len(text))
            if got != text:
                failures.append(f"text_at ({row},{col}): expected {text!r}, got {got!r}")
            continue
        # cell and attr address a single cell
        if not scr.in_bounds(row, col):
            failures.append(f"{kind} ({row},{col}): out of bounds for {scr.rows}x{scr.cols} screen")
            continue
        if kind == "cell":
            if "char" in a:
                got = scr.grid[row][col].char
                if got != a["char"]:
                    failures.append(f"cell ({row},{col}): expected char {a['char']!r}, got {got!r}")
            if isinstance(a.get("attrs"), dict):
                failures.extend(_check_attrs(scr, row, col, a["attrs"], "cell"))
        elif kind == "attr":
            expected = {k: a[k] for k in a if k in ATTR_KEYS}
            failures.extend(_check_attrs(scr, row, col, expected, "attr"))
    return failures


# the live pty drive

def drive_pty(command, keystrokes, rows, cols, timeout):
    """Run command in a REAL pseudo-terminal, feed keystrokes to its stdin, and
    return the raw bytes it emitted.

    POSIX-only: the standard-library pty module requires a POSIX pty, so on a
    platform without one this fails loud rather than pretending to have driven a
    terminal. The pty is put in raw mode so the bytes the renderer sees are
    exactly what the program wrote (no echo of the fed keystrokes, no newline
    translation added by the line discipline).
    """
    try:
        import fcntl
        import os
        import pty
        import struct
        import termios
        import tty
    except ImportError as e:
        raise RuntimeError(
            "terminal runner live drive requires a POSIX pty (stdlib pty/termios); "
            f"this platform lacks it: {e}")

    master, slave = pty.openpty()
    try:
        tty.setraw(slave)
        # advertise the window size so a size-aware TUI lays out to rows x cols
        try:
            winsz = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(slave, termios.TIOCSWINSZ, winsz)
        except OSError:
            pass
        import subprocess
        proc = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave,
                                close_fds=True)
    except FileNotFoundError as e:
        os.close(master)
        os.close(slave)
        raise RuntimeError(f"cannot spawn terminal command {command!r}: {e}")
    os.close(slave)
    for k in keystrokes or []:
        os.write(master, k.encode("utf-8"))
    out = bytearray()
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        r, _, _ = select.select([master], [], [], min(0.2, remaining))
        if r:
            try:
                chunk = os.read(master, 65536)
            except OSError:  # EIO on Linux when the child side has closed
                break
            if not chunk:
                break
            out += chunk
        elif proc.poll() is not None:
            # child exited: drain any bytes still buffered, then stop
            while True:
                r2, _, _ = select.select([master], [], [], 0)
                if not r2:
                    break
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                out += chunk
            break
    try:
        proc.wait(timeout=2)
    except Exception:
        proc.kill()
    os.close(master)
    return bytes(out)


def run_journey(journey):
    """Validate, drive the command in a real pty, render, and grade.

    Returns {"name", "passed", "failures", "error"}. A structural problem is an
    error (not a vacuous pass); a live-drive problem is a named failure.
    """
    result = {"name": journey.get("name") if isinstance(journey, dict) else None,
              "passed": False, "failures": [], "error": None}
    err = validate_journey(journey)
    if err:
        result["error"] = err
        return result
    try:
        data = drive_pty(journey["command"], journey.get("keystrokes"),
                         journey["rows"], journey["cols"],
                         journey.get("timeout", 10))
    except Exception as e:
        result["failures"] = [f"live drive failed: {e}"]
        return result
    scr = render(data, journey["rows"], journey["cols"])
    result["failures"] = evaluate_assertions(scr, journey["assertions"])
    result["passed"] = not result["failures"]
    return result


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    path = Path(argv[1])
    try:
        journey = json.loads(path.read_text())
    except Exception as e:
        print(f"cannot read journey {path}: {e}")
        return 2
    result = run_journey(journey)
    name = result["name"] or str(path)
    if result["error"]:
        print(f"FAIL {name}: {result['error']}")
        print(f"terminal journey FAILED: {name}")
        return 1
    if result["passed"]:
        print(f"PASS {name}")
        print(f"terminal journey PASSED: {name}")
        return 0
    print(f"FAIL {name}")
    for f in result["failures"]:
        print(f"     - {f}")
    print(f"terminal journey FAILED: {name}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
