#!/usr/bin/env python3
"""Install and run, from the artifact an adopter receives.

    python3 scripts/check_install_and_run.py            # every composed pack
    python3 scripts/check_install_and_run.py --pack claude

THE DEFECT THIS MAKES IMPOSSIBLE TO SHIP AGAIN. Veldo 1.0.0 could not be initialised by anyone:
`/veldo:init` failed from every composed pack with "gate template drift" and laid nothing down.
In this repository the template base is a separate tree at engine/; in a COMPOSED PACK the base
has been laid INTO the pack, so the pack root IS the template source and there is no engine/ at
all. The reason it shipped is one sentence in PLAN-0018's ledger: nothing had ever run init from a
composed pack, because every test runs against this repository, which is the one tree nobody
installs.

SO THIS RUNS THE COMPOSED PACK'S OWN SCAFFOLDER, and asserts the tree it ran from has no engine/
directory, because that absence is the condition that broke. THE EXECUTABLE ACTUALLY LAUNCHED IS
WRITTEN DOWN, READ OFF THE COMPLETED LAUNCH rather than off any variable near it, and the tree the
templates came from is derived from THAT path. A RECORD OF AN ARGUMENT IS NOT A RECORD OF A LAUNCH,
and this file has now failed that twice: first the result recorded the directory the function was
PASSED and derived engine/ presence from it, so pointing the launch at this repository left every
provenance row green; then the record was built from a list assigned one line above the call, so
swapping only the CALL left every row green again and printed "(engine/ in that tree: False)" for a
launch out of the tree that has engine/. The record is now subprocess's own args off the
CompletedProcess, which is the launch or nothing.

FIVE STAGES, EACH FAILING BY ITS OWN NAME, because each is a different broken part of an adopter's
first ten minutes:

  COMPOSE_FAILED     the publisher could not produce a tree at all
  NO_PACKS_COMPOSED  it produced a tree with no composed pack, which would make every later
                     assertion vacuous - a loop over an empty set passes while proving nothing
  INIT_FAILED        init refused, or laid nothing, from a composed pack (the 1.0 defect exactly)
  COMMIT_FAILED      the scaffolded tree could not be committed, so its gate would read an EMPTY
                     index and the one required check in the shipped catalog would scan nothing
  ADOPTER_GATE_RED   the scaffolded repository's OWN gate failed

THE SCAFFOLDED TREE IS COMMITTED BEFORE ITS GATE RUNS, and that is not cosmetic. The shipped
catalog's only `required:` slot is scripts/secret_inventory.py and it enumerates through
`git ls-files`, so a review measured this stage laying 83 files down and the required check
reporting "0 scanned" under a green labelled "GATE: GREEN (no-git)". The green was a scan of
nothing. WHAT THAT GREEN CONTAINS IS NOW REPORTED RATHER THAN IMPLIED: how many catalog slots ran,
how many were not applicable, how many files the required check actually scanned against the size
of the tracked corpus, and every built-in that STOOD DOWN by name - a stand-down that is recorded
and not reported reads exactly like a measurement.

THE PACK SET IS DERIVED from what the publisher composed, never typed, and set equality against
that is asserted: a hand-kept list is the defect this repository has shipped twice.

IT MEASURES THE TRACKED TREE, AND THAT IS LOAD-BEARING. The publisher derives the public tree
from TRACKED files, so a brand-new organ that is not yet committed does not exist for an adopter
while this repository's own gate sees it perfectly. This stage caught exactly that within minutes
of existing: a module added to the scaffolder's lay-down list but not yet staged made every
scaffolded repository fail with "template missing" - the 1.0 defect, reintroduced. So a red here
on a new file is often telling you to stage it, not to change it.

IT WRITES ONLY INSIDE A TEMPORARY DIRECTORY, which it removes on a run that RETURNS. It makes no
network call and starts no detached process: every child goes through _run, which is the ONE
launcher in this file so that what is asserted about its keyword arguments is true of every child.
Producing a public tree and publishing it are two acts and this performs only the first.

THE NO-NETWORK PROPERTY IS CARRIED BY WHAT THE CHILDREN CONTAIN, not by an environment flag. This
file used to inject VELDO_NO_NETWORK=1 into every child, which read as a kill-switch and was read by
NOTHING in this repository - a control that appears to enforce and executes nothing is worse than no
control, because it stops the reader looking. It is gone, and the suite instead scans the two things
this stage launches with an interpreter or a shell: scripts/publish.py and the pack's copy of
scripts/verify.sh.
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PUBLISHER = "scripts/publish.py"
PACKS_REL = "packs"
SCAFFOLDER = ".veldo/init_scaffold.py"
ADOPTER_GATE = "scripts/verify.sh"

FAIL_COMPOSE = "COMPOSE_FAILED"
FAIL_NO_PACKS = "NO_PACKS_COMPOSED"
FAIL_INIT = "INIT_FAILED"
FAIL_COMMIT = "COMMIT_FAILED"
FAIL_GATE = "ADOPTER_GATE_RED"
FAILURES = (FAIL_COMPOSE, FAIL_NO_PACKS, FAIL_INIT, FAIL_COMMIT, FAIL_GATE)

# The identity is handed to the one commit rather than written into the throwaway tree's config,
# because the machine's own git identity is not this stage's to assume or to modify.
COMMITTER = ("-c", "user.email=veldo@localhost", "-c", "user.name=veldo install-and-run")

# WHAT THE ADOPTER'S GREEN ACTUALLY CONTAINS, read out of the nested gate's own output. Parsed for
# the REPORT and for one assertion about substance; the pass/fail decision stays on exit codes,
# which no output format can move.
_RE_SCANNED = re.compile(r"(\d+) scanned")
_RE_CATALOG = re.compile(r"^catalog: (\d+) run, (\d+) not-applicable", re.M)
_RE_GATE = re.compile(r"^GATE: (?:GREEN|RED) \((.*)\)\s*$", re.M)
_RE_STAND_DOWN = re.compile(r"^\s*(\S.*?(?:STANDS DOWN|stands down|standing down).*)$", re.M)


def gate_substance(text):
    """The measured content of a nested gate run: slots, scan reach, and every stand-down BY NAME.

    A stand-down recorded and not reported reads exactly like a measurement, which is the defect
    PLAN-0018 finding 64 names. So they are collected here and printed by report_lines, never left
    in a dict for nobody."""
    cat = _RE_CATALOG.search(text or "")
    scan = _RE_SCANNED.search(text or "")
    head = _RE_GATE.search(text or "")
    return {"catalog_run": int(cat.group(1)) if cat else None,
            "catalog_na": int(cat.group(2)) if cat else None,
            "scanned": int(scan.group(1)) if scan else None,
            "commit": head.group(1) if head else None,
            "stand_downs": [s.strip() for s in _RE_STAND_DOWN.findall(text or "")]}

# A composed pack is one that carries the scaffolder: the base has been laid into it. A pack
# directory without one is a pack SOURCE, not a composed artifact, and installing from it would be
# testing the wrong thing.
def composed_packs(pub_root):
    base = Path(pub_root) / PACKS_REL
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.iterdir()
                  if p.is_dir() and (p / SCAFFOLDER).is_file())


# THE ONE LAUNCHER. Every child this stage starts comes through here, which is what makes an
# assertion about this call's keyword arguments an assertion about every child: no session is
# detached, no shell is interposed, nothing is left running when the call returns.
def _run(argv, cwd=None, timeout=900):
    return subprocess.run([str(a) for a in argv], cwd=str(cwd) if cwd else None,
                          capture_output=True, text=True, timeout=timeout)


def commit_tree(target):
    """Stage and commit what init laid down, THEN count what the index holds.

    The scaffolded gate's one required check enumerates through `git ls-files`, so an uncommitted
    tree hands it an empty corpus and it reports "0 scanned" while contributing to a green. Returns
    (proc, tracked_count); tracked_count is None when the commit did not happen, so a caller cannot
    mistake a failed commit for an empty tree."""
    add = _run(["git", "add", "-A"], cwd=target)
    if add.returncode != 0:
        return add, None
    com = _run(["git", *COMMITTER, "commit", "-q", "-m", "init"], cwd=target)
    if com.returncode != 0:
        return com, None
    ls = _run(["git", "ls-files", "-z"], cwd=target)
    if ls.returncode != 0:
        return ls, None
    return com, len([p for p in ls.stdout.split("\0") if p])


def compose(dest, root=None):
    """Produce the public tree with THE REAL PUBLISHER, never a copy of its logic."""
    base = Path(root) if root is not None else ROOT
    proc = _run([sys.executable, base / PUBLISHER, dest], cwd=base)
    return proc


def install_and_run(pack_dir, target, gate=True):
    """Initialise target from THIS COMPOSED PACK and run the scaffolded repository's own gate.

    Returns a dict naming what happened at each stage. The scaffolder is the PACK'S copy, and the
    absence of engine/ in the TREE THE SCAFFOLDER ACTUALLY RAN FROM is recorded because it is the
    condition 1.0 broke on.

    scaffolder_ran is read off the COMPLETED LAUNCH - subprocess's own args on the CompletedProcess
    _run returned - and scaffolder_tree is derived from that path by stripping SCAFFOLDER off its
    tail, so neither can disagree with the launch. TWO WEAKER READS PRECEDED IT AND BOTH WERE DRIVEN
    GREEN: installed_from plus engine/ presence computed from the directory this function was PASSED,
    which survived pointing the launch at this repository; and a record built from an argv list
    assigned one line above the call, which survived swapping the call alone. Each time the run
    reported, falsely, that it had installed from a tree with no engine/ - the exact 1.0 shape,
    reported as its own absence. A launch whose argv names no scaffolder, or names several, leaves
    scaffolder_ran None: an unanswerable read is NAMED here rather than raised out of the stage.

    The tree is COMMITTED between init and the gate, because the shipped catalog's one required check
    reads the index and an uncommitted tree gives it nothing to scan."""
    pack_dir, target = Path(pack_dir), Path(target)
    out = {"pack": pack_dir.name, "installed_from": str(pack_dir),
           "pack_has_engine_dir": (pack_dir / "engine").is_dir(),
           "scaffolder_argv": None, "scaffolder_ran": None, "scaffolder_tree": None,
           "scaffolder_tree_has_engine_dir": None,
           "init_returncode": None, "init_tail": "", "files_created": None,
           "commit_returncode": None, "commit_tail": "", "tracked_files": None,
           "gate_returncode": None, "gate_tail": "", "gate_substance": None, "failure": None}
    target.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "."], cwd=target)

    init = _run([sys.executable, pack_dir / SCAFFOLDER, "."], cwd=target)
    # THE RECORD IS READ OFF THE LAUNCH ITSELF, never off a list assigned beside the call.
    # CompletedProcess.args is the argv subprocess received, so the record and the launch cannot
    # disagree. Building it from a variable one line above the call is not enough and that was
    # MEASURED: with the record still naming the pack's copy and only the call swapped for this
    # repository's own scaffolder, every provenance row stayed green and the stage printed
    # "(engine/ in that tree: False)" for a launch out of the tree that HAS engine/ - the 1.0 shape,
    # reported as its own absence, one level below the read this replaced.
    out["scaffolder_argv"] = [str(a) for a in init.args]
    ran = [a for a in out["scaffolder_argv"] if a.endswith(SCAFFOLDER)]
    # ONE entry is the answer. None, or several, is a state this reader NAMES by leaving the record
    # None rather than raising out of the stage: a raise here would red a wrapper row and take the
    # rows below it out of the run, which is a mutation that deletes coverage rather than failing.
    out["scaffolder_ran"] = ran[0] if len(ran) == 1 else None
    if out["scaffolder_ran"] is not None:
        ran_from = Path(out["scaffolder_ran"]).parents[len(Path(SCAFFOLDER).parts) - 1]
        out["scaffolder_tree"] = str(ran_from)
        out["scaffolder_tree_has_engine_dir"] = (ran_from / "engine").is_dir()
    out["init_returncode"] = init.returncode
    out["init_tail"] = (init.stdout + init.stderr).strip()[-800:]
    created = sum(1 for _ in target.rglob("*") if _.is_file())
    out["files_created"] = created
    if init.returncode != 0 or created == 0:
        out["failure"] = FAIL_INIT
        return out

    if not gate:
        return out
    if not (target / ADOPTER_GATE).is_file():
        out["failure"] = FAIL_INIT
        out["init_tail"] += "\n(no %s was laid down)" % ADOPTER_GATE
        return out
    # THE ADOPTER'S FIRST COMMIT, and it is part of the measurement rather than tidiness: the one
    # `required:` slot the shipped catalog carries enumerates through `git ls-files`.
    com, tracked = commit_tree(target)
    out["commit_returncode"] = com.returncode
    out["commit_tail"] = (com.stdout + com.stderr).strip()[-800:]
    out["tracked_files"] = tracked
    if com.returncode != 0 or not tracked:
        out["failure"] = FAIL_COMMIT
        return out

    g = _run(["bash", ADOPTER_GATE], cwd=target)
    out["gate_returncode"] = g.returncode
    full = g.stdout + g.stderr
    out["gate_tail"] = full.strip()[-1200:]
    out["gate_substance"] = gate_substance(full)
    if g.returncode != 0:
        out["failure"] = FAIL_GATE
    return out


def check(root=None, only=None, gate=True, composer=None):
    """Compose, then install and run every composed pack. Returns (ok, report).

    composer is a SEAM defaulting to the real publisher, present so the vacuous-run guard below can
    be driven: a guard against an empty pack set that nothing ever drives is itself the vacuous shape
    it exists to prevent. fleet.py injects its spawner and waiter for the same reason."""
    base = Path(root) if root is not None else ROOT
    compose_fn = composer if composer is not None else compose
    report = {"composed": [], "installed": [], "results": [], "failure": None, "note": None}
    tmp = tempfile.mkdtemp(prefix="veldo-install-and-run-")
    try:
        pub = Path(tmp) / "public"
        proc = compose_fn(pub, base)
        if proc.returncode != 0:
            report["failure"] = FAIL_COMPOSE
            report["note"] = (proc.stdout + proc.stderr).strip()[-1200:]
            return False, report
        report["composed"] = composed_packs(pub)
        if not report["composed"]:
            report["failure"] = FAIL_NO_PACKS
            report["note"] = ("the publisher produced a tree with no composed pack, so installing "
                              "from one would prove nothing")
            return False, report
        wanted = [p for p in report["composed"] if only in (None, p)]
        if only is not None and not wanted:
            report["failure"] = FAIL_NO_PACKS
            report["note"] = "no composed pack named %r" % only
            return False, report
        for name in wanted:
            res = install_and_run(pub / PACKS_REL / name, Path(tmp) / ("fresh-" + name), gate)
            report["results"].append(res)
            report["installed"].append(name)
            if res["failure"] and report["failure"] is None:
                report["failure"] = res["failure"]
        return report["failure"] is None, report
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def report_lines(report):
    lines = []
    if report["failure"] == FAIL_COMPOSE:
        return ["install-and-run: %s - the publisher could not produce a tree.\n%s"
                % (FAIL_COMPOSE, report["note"])]
    if report["failure"] == FAIL_NO_PACKS:
        return ["install-and-run: %s - %s" % (FAIL_NO_PACKS, report["note"])]
    lines.append("install-and-run: %d composed pack(s) derived from the publisher: %s"
                 % (len(report["composed"]), ", ".join(report["composed"])))
    for r in report["results"]:
        state = "GREEN" if r["failure"] is None else r["failure"]
        # BOTH PATHS, because they answer different questions and the line used to answer only the
        # first while sounding like it answered the second: the pack it installed FROM is where the
        # bytes were written, and the scaffolder it RAN is the provenance claim. They agree except in
        # the one case this stage exists to catch, and then the difference is on the line.
        lines.append("  %-12s installed %d file(s) from %s (scaffolder run: %s, engine/ in that "
                     "tree: %s) -> adopter gate %s"
                     % (r["pack"], r["files_created"] or 0, r["installed_from"],
                        r["scaffolder_ran"], r["scaffolder_tree_has_engine_dir"], state))
        # WHAT THAT GREEN CONTAINS, on the line. "Their gate went green" over a catalog whose one
        # required check scanned zero files is a true sentence about a measurement of nothing, and
        # a reader cannot tell the two apart from the word GREEN.
        sub = r["gate_substance"]
        if sub:
            lines.append("    their gate: %s catalog slot(s) ran, %s not-applicable; the required "
                         "check scanned %s of %s tracked file(s); commit %s"
                         % (sub["catalog_run"], sub["catalog_na"], sub["scanned"],
                            r["tracked_files"], sub["commit"]))
            # RECORDED IS NOT REPORTED. A built-in that stood down contributed a pass it did not
            # measure, so each one is named rather than counted into the green.
            for sd in sub["stand_downs"]:
                lines.append("      stood down (recorded, not measured): %s" % sd)
            if not sub["stand_downs"]:
                lines.append("      no built-in stood down: every slot that ran, measured")
        if r["failure"] == FAIL_INIT and r["init_tail"]:
            lines.append("    init said: %s" % r["init_tail"].replace("\n", "\n      "))
        if r["failure"] == FAIL_COMMIT:
            lines.append("    the scaffolded tree could NOT be committed, so its gate would have "
                         "read an empty index: %s" % r["commit_tail"].replace("\n", "\n      "))
        if r["failure"] == FAIL_GATE and r["gate_tail"]:
            lines.append("    THEIR gate said: %s" % r["gate_tail"].replace("\n", "\n      "))
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pack", default=None, help="install only this composed pack")
    ap.add_argument("--no-gate", action="store_true",
                    help="install only, do not run the adopter's gate (diagnostic)")
    args = ap.parse_args(argv)
    ok, report = check(only=args.pack, gate=not args.no_gate)
    for line in report_lines(report):
        print(line)
    print("install-and-run: %s" % ("pass" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
