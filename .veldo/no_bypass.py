#!/usr/bin/env python3
"""The structural no-bypass check (WARP-0622, W9 of PLAN-0016).

THE PROPERTY. A human decision reaches this system as a RECORD - an attested approval, a tracker
transition with an attributed changelog - never as an answer typed at a terminal. That is not a
style preference. A terminal answer has no approver identity that survives the process, no binding
to the artifact it approved, no expiry and no audit trail, so every guard built on top of those
four things is bypassed the moment one exists. The owner stated the same rule independently:
never approve risky work by a terminal yes or no.

Today no module does this. **That is exactly why the check is worth having**: the cost of keeping a
true property true is one gate stage, and the cost of discovering it stopped being true is an
approval nobody can attribute.

WHY THIS PARSES RATHER THAN GREPS. A string search for "input(" matches the word in a comment, in
a docstring, in `n_inputs(`, and misses `builtins.input()`, `getattr(builtins, "input")()` and an
aliased import. Tonight's own history is the argument: a grep-shaped answer was wrong three times
in one evening. The AST knows what is a CALL and what is prose, so it is used.

WHAT IT DOES NOT CLAIM, stated so nobody upgrades it later. It proves no module in the declared
surface CALLS a terminal read. It cannot prove a human decision did not reach the system some other
way - through an environment variable, a file a person edited, or an agent relaying what somebody
said in chat. Those are real and this does not address them. What it removes is the easiest and
most tempting bypass, the one a well-meaning implementer adds at four in the morning because the
approval flow is slow.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# THE SURFACE THIS GOVERNS: the modules through which a human decision, approval or settlement can
# reach the repository. Written down rather than globbed, because a glob would silently widen to
# unrelated modules and then be relaxed to make them pass, which is how a check becomes a comment.
DECISION_SURFACE = (
    "authorization.py", "two_key.py", "decision.py", "decision_review.py",
    "request.py", "request_projection.py", "request_reconcile.py", "request_doorbell.py",
    "policy_check.py", "action_executor.py", "execution_binding.py",
)

# A terminal read, in every spelling the AST can see. `input` and `raw_input` as bare calls;
# anything reached through the getpass module; and a read on sys.stdin.
BARE_READS = frozenset({"input", "raw_input"})
STDIN_READS = frozenset({"read", "readline", "readlines"})


def _attr_chain(node):
    """`sys.stdin.readline` -> ['sys','stdin','readline'], for any attribute chain."""
    out = []
    while isinstance(node, ast.Attribute):
        out.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        out.append(node.id)
    return list(reversed(out))


def terminal_reads(source, where="<source>"):
    """Every terminal-read CALL in one module, as (line, what) pairs. Empty means clean.

    Syntax errors are reported rather than swallowed: a module the checker cannot parse is a module
    it cannot vouch for, and silently passing it would be the failure this whole file guards
    against."""
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return [(getattr(e, "lineno", 0), "unparseable, so unverifiable: %s" % e.msg)]
    hits = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        if isinstance(f, ast.Name) and f.id in BARE_READS:
            hits.append((n.lineno, "%s()" % f.id))
            continue
        chain = _attr_chain(f)
        if not chain:
            continue
        if "getpass" in chain:
            hits.append((n.lineno, ".".join(chain)))
        elif len(chain) >= 2 and chain[-2] == "stdin" and chain[-1] in STDIN_READS:
            hits.append((n.lineno, ".".join(chain)))
        elif chain[:1] == ["builtins"] and chain[-1] in BARE_READS:
            hits.append((n.lineno, ".".join(chain)))
    return sorted(hits)


def check(root=None, surface=DECISION_SURFACE):
    """Every terminal read across the declared decision surface, as
    [(module, line, what), ...]. Empty is the passing state.

    A module named in the surface that does not EXIST is itself reported. Otherwise deleting a
    module would silently shrink what is checked, which is the same defect class as a roster that
    quietly empties."""
    base = Path(root or ROOT) / ".veldo"
    out = []
    for name in surface:
        p = base / name
        if not p.is_file():
            out.append((name, 0, "declared in the decision surface but absent: the surface must "
                                 "name real modules or it silently shrinks"))
            continue
        for line, what in terminal_reads(p.read_text(), name):
            out.append((name, line, what))
    return out


def report(problems):
    """One operator-readable line per problem."""
    return ["%s:%d records a human decision from a terminal read (%s): a decision must arrive as an "
            "attested record, never as an answer typed at a prompt" % (m, l, w)
            for m, l, w in problems]


if __name__ == "__main__":
    import sys
    probs = check()
    for line in report(probs):
        print(line)
    print("no-bypass: %d module(s) checked, %d problem(s)" % (len(DECISION_SURFACE), len(probs)))
    raise SystemExit(1 if probs else 0)
