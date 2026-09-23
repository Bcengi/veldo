"""Scope coverage reads a plain-string inner scope as ONE named scope, never as the empty set.

The claim receiver asks whether a member's scope covers this repository by passing the repository id
as a string. control_membership._scope_set read any non-list as the empty set, and the empty set is a
subset of every set, so every named scope covered every repository. Found through VELDO-0064's review
(2026-09-23); the fix is in control_membership.scope_covers.
"""
import importlib.util as _sc_ilu


def _sc_load(name, path):
    spec = _sc_ilu.spec_from_file_location(name, path)
    mod = _sc_ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_sc_cm = _sc_load('scope_membership', ROOT / ".veldo" / "control_membership.py")
expect('VELDO-0025 membership/scope-covers-named-string: a named scope covers a repository id only if it '
       "lists it; '*' covers it; a malformed inner scope is refused rather than read as empty",
       not _sc_cm.scope_covers(["PROJ-A"], "repo-1") and _sc_cm.scope_covers(["repo-1"], "repo-1")
       and _sc_cm.scope_covers("*", "repo-1") and _sc_cm.scope_covers(["repo-1", "PROJ-A"], "repo-1")
       and not _sc_cm.scope_covers(["X"], 5) and not _sc_cm.scope_covers(["X"], ["X", 3])
       and not _sc_cm.scope_covers(["X"], None) and not _sc_cm.scope_covers(["X"], "*"))
expect('VELDO-0025 membership/scope-forms-agree: a list naming "*" is universal as either argument, and a '
       'string is one named scope as either argument, so a member enrolled with scope "repo-1" covers repo-1',
       _sc_cm.scope_covers(["*"], "repo-1") and _sc_cm.scope_covers(["*"], ["*"]) and _sc_cm.scope_covers("*", ["*"])
       and not _sc_cm.scope_covers(["repo-1"], ["*"]) and _sc_cm.scope_covers("repo-1", "repo-1")
       and not _sc_cm.scope_covers("repo-1", "repo-2") and not _sc_cm.scope_covers({"x": 1}, "repo-1")
       and not _sc_cm.scope_covers(None, "repo-1"))

