#!/usr/bin/env python3
"""VELDO design-token linter (reference).

The design contract's first layer is tokens: screens are built from named
design tokens, never raw values, so a screen is on-design by construction and
the gate can prove it. This linter fails a file that hardcodes a color or a
spacing value the token set already names - the raw value is exactly the drift
the token layer exists to prevent.

  token_lint.py <tokens.json> <file> [file ...]

tokens.json:
  {
    "colors":  {"--brand": "#1a73e8", "--ink": "#101418"},
    "space":   {"--s-1": "4px", "--s-2": "8px"},
    "allow_raw": ["0", "0px", "1px", "100%", "transparent", "currentColor"]
  }

A raw hex/rgb color, or a px value that is not in allow_raw, is a violation:
the token set covers it, so the literal is drift. Declaring a value in
allow_raw is the conscious exception. Exit 0 = clean, 1 = violations (printed
with file:line).
"""
import json
import re
import sys
from pathlib import Path

HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
RGB = re.compile(r"\brgba?\(")
PX = re.compile(r"(?<![\w.])\d+(?:\.\d+)?px\b")


def load_tokens(path):
    data = json.loads(Path(path).read_text())
    allow = set(data.get("allow_raw", []))
    # token VALUES are legitimate literals only inside the tokens file itself;
    # in source, they must be referenced by name, so every literal is drift.
    return allow


def lint_file(path, allow):
    violations = []
    for n, line in enumerate(Path(path).read_text().splitlines(), 1):
        code = line.split("/*", 1)[0].split("//", 1)[0]
        for m in HEX.finditer(code):
            violations.append((n, "raw-color", m.group(0)))
        for m in RGB.finditer(code):
            violations.append((n, "raw-color", m.group(0) + "...)"))
        for m in PX.finditer(code):
            if m.group(0) not in allow:
                violations.append((n, "raw-space", m.group(0)))
    return violations


def lint(tokens_path, files):
    allow = load_tokens(tokens_path)
    total = 0
    for f in files:
        vs = lint_file(f, allow)
        for (n, rule, val) in vs:
            print(f"{f}:{n}: {rule}: {val} (use a design token)")
        total += len(vs)
    if total:
        print(f"token lint: {total} violation(s)")
        return 1
    print("token lint: clean")
    return 0


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    return lint(sys.argv[1], sys.argv[2:])


if __name__ == "__main__":
    sys.exit(main())
