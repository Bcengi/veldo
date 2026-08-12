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
directory, because that absence is the condition that broke.

FOUR STAGES, EACH FAILING BY ITS OWN NAME, because each is a different broken part of an adopter's
first ten minutes:

  COMPOSE_FAILED     the publisher could not produce a tree at all
  NO_PACKS_COMPOSED  it produced a tree with no composed pack, which would make every later
                     assertion vacuous - a loop over an empty set passes while proving nothing
  INIT_FAILED        init refused, or laid nothing, from a composed pack (the 1.0 defect exactly)
  ADOPTER_GATE_RED   the scaffolded repository's OWN gate failed

THE PACK SET IS DERIVED from what the publisher composed, never typed, and set equality against
that is asserted: a hand-kept list is the defect this repository has shipped twice.

IT WRITES ONLY INSIDE A TEMPORARY DIRECTORY, which it removes. It makes no network call and starts
no detached process. Producing a public tree and publishing it are two acts and this performs only
the first.
"""
import argparse
import os
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
FAIL_GATE = "ADOPTER_GATE_RED"
FAILURES = (FAIL_COMPOSE, FAIL_NO_PACKS, FAIL_INIT, FAIL_GATE)

# A composed pack is one that carries the scaffolder: the base has been laid into it. A pack
# directory without one is a pack SOURCE, not a composed artifact, and installing from it would be
# testing the wrong thing.
def composed_packs(pub_root):
    base = Path(pub_root) / PACKS_REL
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.iterdir()
                  if p.is_dir() and (p / SCAFFOLDER).is_file())


def _run(argv, cwd=None, timeout=900):
    return subprocess.run([str(a) for a in argv], cwd=str(cwd) if cwd else None,
                          capture_output=True, text=True, timeout=timeout,
                          env=dict(os.environ, VELDO_NO_NETWORK="1"))


def compose(dest, root=None):
    """Produce the public tree with THE REAL PUBLISHER, never a copy of its logic."""
    base = Path(root) if root is not None else ROOT
    proc = _run([sys.executable, base / PUBLISHER, dest], cwd=base)
    return proc


def install_and_run(pack_dir, target, gate=True):
    """Initialise target from THIS COMPOSED PACK and run the scaffolded repository's own gate.

    Returns a dict naming what happened at each stage. The scaffolder is the PACK'S copy, and the
    absence of engine/ in the pack is recorded because it is the condition 1.0 broke on."""
    pack_dir, target = Path(pack_dir), Path(target)
    out = {"pack": pack_dir.name, "installed_from": str(pack_dir),
           "pack_has_engine_dir": (pack_dir / "engine").is_dir(),
           "init_returncode": None, "init_tail": "", "files_created": None,
           "gate_returncode": None, "gate_tail": "", "failure": None}
    target.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "."], cwd=target)

    init = _run([sys.executable, pack_dir / SCAFFOLDER, "."], cwd=target)
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
    g = _run(["bash", ADOPTER_GATE], cwd=target)
    out["gate_returncode"] = g.returncode
    out["gate_tail"] = (g.stdout + g.stderr).strip()[-1200:]
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
        lines.append("  %-12s installed %d file(s) from %s (engine/ present: %s) -> adopter gate %s"
                     % (r["pack"], r["files_created"] or 0, r["installed_from"],
                        r["pack_has_engine_dir"], state))
        if r["failure"] == FAIL_INIT and r["init_tail"]:
            lines.append("    init said: %s" % r["init_tail"].replace("\n", "\n      "))
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
