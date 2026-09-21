#!/usr/bin/env python3
"""The VELDO-0029 driven record: run the spec's own suite fragment the way the dispatcher runs it
(shared.py's namespace, then the fragment), with `expect` recording every row instead of counting,
and write proof/VELDO-0029/driven.json.

The mutants are INSIDE the fragment: every DRIVEN row applies a mutation to a copy of the engine or
of the contract module, runs the same harness, and asserts the named row reds while the unmutated
copy passes it. So the record is the row list of one run, with the driven rows and the declared
falsifiers called out, plus the commit and the suite digest it was taken at. It runs nothing
detached, writes only this file, and is a record, never a gate claim: the gate is the gate.

  python3 proof/VELDO-0029/drive.py
"""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUITES = ROOT / "scripts" / "suites"
FRAGMENT = SUITES / "46_veldo_0029_enrollment.py"
OUT = Path(__file__).resolve().parent / "driven.json"

FALSIFIERS = {
    "AC1": "enrollment/an-unsigned-binding-is-not-a-binding",
    "AC2": "enrollment/ambient-sources-decide-nothing",
    "AC3": "enrollment/a-replaced-clone-must-enroll-again",
    "AC4": "enrollment/a-refusal-hands-back-no-path",
}


def main():
    import types
    shared = types.ModuleType("veldo_suite_shared_drive")
    shared.__dict__["__file__"] = str(SUITES / "shared.py")
    exec(compile((SUITES / "shared.py").read_text(), str(SUITES / "shared.py"), "exec"), shared.__dict__)
    rows = []

    def expect(name, condition):
        rows.append({"label": name, "passed": bool(condition)})

    shared.__dict__["expect"] = expect
    shared.__dict__["__suite_file__"] = str(FRAGMENT)
    exec(compile(FRAGMENT.read_text(), str(FRAGMENT), "exec"), shared.__dict__)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), capture_output=True, text=True).stdout.strip()
    # The negative control names DRIVEN in its own sentence, so it would be counted as a driven row
    # by a naive search. It is the opposite of one: it asserts a copy that changes NOTHING agrees.
    driven = [r for r in rows if "DRIVEN" in r["label"] and " control " not in r["label"]]
    by_ac = {}
    for r in rows:
        for ac in ("AC1", "AC2", "AC3", "AC4"):
            # Matched at the label's HEAD, not anywhere in it. A row whose prose names another
            # criterion - the oracle row explains that agreeing with YAML on a leading zero would be
            # the defect AC2 exists to prevent - was being counted against that one as well.
            if r["label"].startswith("VELDO-0029 %s " % ac):
                by_ac.setdefault(ac, {"rows": 0, "passed": 0, "driven": 0})
                by_ac[ac]["rows"] += 1
                by_ac[ac]["passed"] += int(r["passed"])
                by_ac[ac]["driven"] += int("DRIVEN" in r["label"])
    record = {
        "schema": "veldo.driven/v1",
        "spec_id": "VELDO-0029",
        "commit": commit,
        "taken_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fragment": str(FRAGMENT.relative_to(ROOT)),
        "fragment_sha256": hashlib.sha256(FRAGMENT.read_bytes()).hexdigest(),
        "description": ("One run of the spec's suite fragment with every row recorded. Every DRIVEN row applies "
                        "a mutation to a copy of .veldo/control_enrollment.py, runs the same real git fixtures "
                        "- two clones of different repositories, a linked worktree, a directory swapped for a "
                        "clone of another repository, a fresh clone of the same one, and a directory that is "
                        "not a repository - and requires the named row red while the unmutated copy passes it. "
                        "One row is the negative control: a copy carrying only an added comment, required to "
                        "agree with the original on every case the other rows turn on. The signer is an HMAC "
                        "the suite supplies, because the module holds no key material and takes signing and "
                        "verification as callables; what the rows turn on is that the signature is CHECKED. "
                        "No model is called and nothing is spent."),
        "external_drives": [
            {"falsifier": "AC2 enrollment/ambient-sources-decide-nothing",
             "mutation": ".veldo/control_enrollment.py: _git stops stripping the GIT_ environment, which is "
                         "the state the row CAUGHT before this item landed: GIT_DIR overrides `git -C`, so "
                         "`git -C repoA rev-list --max-parents=0 HEAD` answered repoB's root commit while "
                         "believing it had named repoA, and the identity check compared the wrong repository "
                         "against the binding",
             "result": "AC2 RED, the other four rows pass"},
        ],
        "rows_total": len(rows),
        "rows_passed": sum(1 for r in rows if r["passed"]),
        "rows_failed": [r["label"] for r in rows if not r["passed"]],
        "driven_rows": [r["label"] for r in driven],
        "declared_falsifiers": {ac: {"row_contains": frag,
                                     "present": any(frag in r["label"] for r in rows),
                                     "passed": any(frag in r["label"] and r["passed"] for r in rows)}
                                for ac, frag in FALSIFIERS.items()},
        "per_criterion": by_ac,
        "rows": rows,
    }
    OUT.write_text(json.dumps(record, indent=2) + "\n")
    print("driven.json: %d rows, %d passed, %d driven, falsifiers %s"
          % (len(rows), record["rows_passed"], len(driven),
             {k: v["passed"] for k, v in record["declared_falsifiers"].items()}))
    return 0 if not record["rows_failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
