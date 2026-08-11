#!/usr/bin/env python3
"""Produce the PUBLIC tree from this private repository (WARP-1704, W4 of PLAN-0017).

    python3 scripts/publish.py DEST          # build the public tree at DEST
    python3 scripts/publish.py DEST --check  # build it, then re-build and compare (idempotence)

IT PUSHES NOTHING. The only output is a directory on this machine. Producing a public tree and
publishing it are two acts, and the second is two-keyed at W6.

**DERIVED, NEVER CURATED, AND DEFAULT DENY.** The tree is the result of applying INCLUDE globs to
the repository. A path matching no rule is ABSENT, so the pipeline never has to know what is secret,
only what is publishable. That is the safe direction to fail in: when this repository grows a
directory nobody remembered to think about, the new directory is missing from the public tree rather
than published by an exclusion list that was never updated.

A curated copy would be a judgement repeated by hand every release, and judgement degrades with
familiarity - the tenth release is copied by someone who has stopped reading.

**THE SCAN READS THE OUTPUT.** Sweeping the source proves nothing about the copy, because the copy
is made by different code than the sweep reads. What is scanned is exactly what would be pushed.

**IT REFUSES RATHER THAN CLEANS.** On a finding it fails and writes nothing further. A cleaner would
make the output depend on a substitution nobody reviewed, and would train us to ignore the very
finding it just repaired.
"""

import argparse
import importlib.util as _ilu
import filecmp
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# WHAT SHIPS. Globs against the tracked file list, in git's own path syntax. This is the whole
# decision about the public tree, in one reviewable place.
INCLUDE = (
    "engine/**",                    # the base every pack extends
    "packs/**",                     # the seven packs, composed with the base at build time
    "docs/*.md",                    # the generic documents
    "docs/training/**",
    "README.md",
    "VELDO.md",
    "LICENSE",
    "NOTICE",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    ".claude-plugin/marketplace.json",   # so Claude Code can install the pack
)

# CARVED OUT OF AN INCLUDED PREFIX, and each one is a decision rather than an oversight. These sit
# under `docs/` but are internal provenance: design notes and research carry the reasoning, the
# rejected options and the customer context that produced a decision.
EXCLUDE = (
    "docs/design/**",
    "docs/research/**",
    "**/__pycache__/**",
    "**/*.pyc",
    # PLAN-0014's foundation, held back from 1.0 DELIBERATELY. These four modules are gate green
    # with real teeth and clean on every criterion the release audit applied, and they have not had
    # their own independent review, which this method requires before something ships. Five rounds
    # of confirmation examined a tree without them; adding unreviewed capability at the last moment
    # would make the release something other than what was reviewed. Half of a plan is also worse
    # than none of it: W3, W4, W5 and W8 are still to build. They ship in the release after this.
    "engine/.veldo/estimate.py",
    "engine/.veldo/toe_normalize.py",
    "engine/.veldo/judgment_load.py",
    "engine/.veldo/cost_to_change.py",
    "engine/.veldo/examples/estimate-example.yaml",
)

PRIVATE_NAMES = ROOT / ".veldo" / "private_names.txt"

# The repository's own distribution coordinates are not a company reference. Stripped before
# matching, exactly as the gate's genericity sweep does, so the owner's account name in a clone URL
# does not read as a customer leak.
OWN_COORDINATES = ("Bcengi/veldo", "Dejitech, Inc.", "Dejitech")

BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".ico", ".woff", ".woff2", ".zip",
                   ".pyc", ".webp"}


def load_private_names(path=PRIVATE_NAMES):
    """The one list, shared with the gate's genericity sweep. Fails closed if it is missing or
    empty: a leak scan with nothing to look for is worse than no scan, because it reports green."""
    if not path.is_file():
        raise SystemExit("publish: %s is missing; refusing to scan for nothing" % path)
    names = [ln.strip() for ln in path.read_text("utf-8").splitlines()]
    names = [n for n in names if n and not n.startswith("#")]
    if not names:
        raise SystemExit("publish: %s declares no names; refusing to scan for nothing" % path)
    return names


def tracked_files():
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files"],
                         capture_output=True, text=True, check=True)
    return sorted(out.stdout.split("\n0")[0].split())


def _glob_re(pattern):
    """git-style glob to regex. `**` crosses directories, `*` does not."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?"); i += 3
        elif pattern.startswith("**", i):
            out.append(".*"); i += 2
        elif pattern[i] == "*":
            out.append("[^/]*"); i += 1
        elif pattern[i] == "?":
            out.append("[^/]"); i += 1
        else:
            out.append(re.escape(pattern[i])); i += 1
    return re.compile("^" + "".join(out) + "$")


_INCLUDE_RE = [_glob_re(p) for p in INCLUDE]
_EXCLUDE_RE = [_glob_re(p) for p in EXCLUDE]


def selected(files):
    """The published set: included by a rule and not carved out. Default deny."""
    out = []
    for rel in files:
        if any(r.match(rel) for r in _EXCLUDE_RE):
            continue
        if any(r.match(rel) for r in _INCLUDE_RE):
            out.append(rel)
    return sorted(out)


def compose_packs(dest, engine_rel="engine", packs_rel="packs"):
    """Lay the base under every pack, so one published pack directory is a working install.

    packs/README.md tells an adopter to take the base and their pack; a published release ships each
    pack already composed so that is one directory. The private repository keeps ONE base and no
    copies - composition belongs at publication, not in git, because seven copies in git is seven
    things to drift."""
    engine = dest / engine_rel
    if not engine.is_dir():
        return []
    composed = []
    for pack in sorted(p for p in (dest / packs_rel).iterdir() if p.is_dir()):
        for src in sorted(engine.rglob("*")):
            if not src.is_file():
                continue
            target = pack / src.relative_to(engine)
            if target.exists():
                continue  # the pack's own file WINS, which is what extending means
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
        # THE LICENCE TRAVELS WITH THE DIRECTORY. packs/README.md tells an adopter a published pack
        # is one directory they can take, and a directory of code with no licence in it is a
        # directory nobody's legal team will let them use. It lives at the root too; this puts it
        # where someone who copied only the pack will actually find it.
        # THE PUBLISHED PACK SHIPS AS IF INIT HAD RUN, and it has to. The base leaves the unit and
        # dependency-audit slots BLANK on purpose, so an unconfigured gate stays red until a human
        # declares them, and `veldo init` fills them when it lays the gate down. In a composed pack
        # every file already exists, so init skips verify.sh and the blanks survive: the adopter's
        # first run is red on two slots and init cannot help them, because there is nothing left for
        # it to create. So composition applies the SAME transform init applies, imported from
        # init_scaffold rather than restated here, because two copies of the starter gate would
        # disagree the first time one changed.
        gate = pack / "scripts" / "verify.sh"
        if gate.is_file():
            spec = _ilu.spec_from_file_location("veldo_init_scaffold", engine / ".veldo" / "init_scaffold.py")
            mod = _ilu.module_from_spec(spec)
            _prev = sys.dont_write_bytecode
            sys.dont_write_bytecode = True   # do not litter the tree we are publishing
            try:
                spec.loader.exec_module(mod)
            finally:
                sys.dont_write_bytecode = _prev
            gate.write_text(mod._starter_gate(gate.read_text()), "utf-8")
        for extra in ("LICENSE", "NOTICE"):
            src = dest / extra
            if src.is_file() and not (pack / extra).exists():
                shutil.copy2(src, pack / extra)
        composed.append(pack.name)
    return composed


# THIS MACHINE'S PATHS ARE A LEAK IN THEIR OWN RIGHT, separate from the name list: a build path
# discloses the username, the directory layout and often the project it was built from.
#
# A build path is an ABSOLUTE path, so the marker has to START one. A bare substring test cannot
# tell `/path/to/repo/projects` from `GET /api/v1/home/`, and it called the second one a leak: the
# route is the product's own URL and redacting it would corrupt a documented endpoint. So each
# marker carries a pattern requiring that it is not preceded by another path segment. This only
# ever NARROWS what is ignored: a marker nested inside a longer path cannot be an absolute build
# path, and every genuine one (line start, after whitespace, after a quote, after `=`) still
# matches. The substring test is kept as the cheap gate before the regex runs.
_NOT_NESTED = r"(?<![A-Za-z0-9_.\-/])"
BUILD_PATH_MARKERS = (
    ("/home/", re.compile(_NOT_NESTED + r"/home/[A-Za-z0-9_.\-]+")),
    ("/Users/", re.compile(_NOT_NESTED + r"/Users/[A-Za-z0-9_.\-]+")),
    ("/tmp/claude", re.compile(r"/tmp/claude")),
    ("C:\\Users\\", re.compile(r"C:\\Users\\")),
)


def scan(dest, names):
    """Every file of the PRODUCED tree against the private-name list. Returns [(rel, name, line)]."""
    findings = []
    lowered = [(n, n.lower()) for n in names]
    for p in sorted(dest.rglob("*")):
        if not p.is_file():
            continue
        # EVERY FILE, DECODED LENIENTLY. This used to skip anything with a binary extension, and a
        # compiled cache file then carried the build machine's path - username and a private name
        # included - straight past a scan that reported clean. A leak does not care what extension
        # it wears. Undecodable bytes become replacement characters, which is fine: what matters is
        # that an ASCII name embedded in a binary is still found.
        try:
            text = p.read_text("utf-8", errors="replace")
        except OSError:
            continue
        for coord in OWN_COORDINATES:
            text = text.replace(coord, "")
        low = text.lower()
        for mark, pat in BUILD_PATH_MARKERS:
            if mark.lower() in low and pat.search(text):
                findings.append((str(p.relative_to(dest)), "build path " + mark, 0))
                break
        for original, needle in lowered:
            if needle in low:
                for n, line in enumerate(text.splitlines(), 1):
                    if needle in line.lower():
                        findings.append((str(p.relative_to(dest)), original, n))
                        break
    return findings


def build(dest, quiet=False):
    """Produce the tree at dest. Returns (files_written, composed_packs). Refuses on a finding."""
    dest = Path(dest).resolve()
    if dest == ROOT or ROOT in dest.parents or dest in ROOT.parents:
        raise SystemExit("publish: refusing a destination inside or containing this repository: %s"
                         % dest)
    names = load_private_names()
    rels = selected(tracked_files())
    if not rels:
        raise SystemExit("publish: the manifest selected NOTHING; refusing to publish an empty tree")
    if dest.exists():
        shutil.rmtree(dest)
    for rel in rels:
        src, target = ROOT / rel, dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    composed = compose_packs(dest)
    # SWEEP THE TREE FOR CACHE DIRECTORIES AFTER COMPOSING, because anything that imports a module
    # out of the tree can create one and the manifest cannot exclude what does not exist yet.
    for cache in sorted(dest.rglob("__pycache__")):
        shutil.rmtree(cache, ignore_errors=True)
    findings = scan(dest, names)
    if findings:
        print("publish: REFUSED. The produced tree carries private names:")
        for rel, name, line in findings[:40]:
            print("  %s:%d  %r" % (rel, line, name))
        if len(findings) > 40:
            print("  ... and %d more" % (len(findings) - 40))
        print("Nothing was cleaned and nothing further was written. A finding here is a decision for")
        print("a person: the name belongs in the source, or the file does not belong in the manifest.")
        raise SystemExit(1)
    if not quiet:
        print("publish: %d file(s) -> %s" % (len(rels), dest))
        print("publish: composed %d pack(s) with the base: %s" % (len(composed), ", ".join(composed)))
        print("publish: leak scan clean over the PRODUCED tree against %d private name(s)" % len(names))
    return rels, composed


def _identical(a, b):
    """Byte-identical trees, compared both ways so a file present in only one is caught."""
    cmpd = filecmp.dircmp(str(a), str(b))

    def walk(d):
        if d.left_only or d.right_only or d.funny_files or d.diff_files:
            return False
        return all(walk(sub) for sub in d.subdirs.values())
    return walk(cmpd)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("dest")
    ap.add_argument("--check", action="store_true",
                    help="build twice and compare, proving the pipeline is idempotent")
    a = ap.parse_args(argv[1:])
    rels, _ = build(a.dest)
    if a.check:
        second = Path(str(a.dest).rstrip("/") + ".idempotence-check")
        build(second, quiet=True)
        same = _identical(Path(a.dest), second)
        shutil.rmtree(second)
        if not same:
            raise SystemExit("publish: NOT IDEMPOTENT - two runs over an unchanged repository "
                             "produced different trees")
        print("publish: idempotent (two runs over an unchanged repository are byte-identical)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
