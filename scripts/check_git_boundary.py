#!/usr/bin/env python3
"""Reject Git argument vectors outside the one neutralized subprocess boundary."""
import ast
from pathlib import Path


def problems(source, funnel=False):
    tree = ast.parse(source)
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    bad = []
    for node in ast.walk(tree):
        vector = (isinstance(node, (ast.List, ast.Tuple)) and node.elts
                  and isinstance(node.elts[0], ast.Constant) and node.elts[0].value == "git")
        if not vector:
            continue
        parent = parents.get(node)
        while isinstance(parent, ast.BinOp):
            parent = parents.get(parent)
        if funnel and isinstance(parent, ast.Call) and isinstance(parent.func, ast.Name) and parent.func.id == "_run":
            continue
        if not (isinstance(parent, ast.Call) and isinstance(parent.func, ast.Attribute)
                and isinstance(parent.func.value, ast.Name)
                and parent.func.value.id == "_git_process"
                and parent.func.attr in ("run", "check_output")):
            bad.append(node.lineno)
    return bad


def check(root):
    return [f"{path.relative_to(root)}:{line}: Git must use git_process"
            for directory in (".veldo", "engine/.veldo", "scripts", "engine/scripts")
            for path in (Path(root) / directory).glob("*.py") if path.name != "git_process.py"
            for line in problems(path.read_text(), funnel=path.name == "check_install_and_run.py")]


if __name__ == "__main__":
    errors = check(Path(__file__).resolve().parent.parent)
    print("\n".join(errors) if errors else "Git subprocess boundary: pass")
    raise SystemExit(bool(errors))
