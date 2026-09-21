#!/usr/bin/env python3
"""The VELDO-0107 driven record: run the spec's own suite fragment the way the dispatcher runs it
(shared.py's namespace, then the fragment), with `expect` recording every row instead of counting,
and write proof/VELDO-0107/driven.json.

The mutants are INSIDE the fragment: every DRIVEN row applies a mutation to a copy of the engine or
of the contract module, runs the same harness, and asserts the named row reds while the unmutated
copy passes it. So the record is the row list of one run, with the driven rows and the declared
falsifiers called out, plus the commit and the suite digest it was taken at. It runs nothing
detached, writes only this file, and is a record, never a gate claim: the gate is the gate.

  python3 proof/VELDO-0107/drive.py
"""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUITES = ROOT / "scripts" / "suites"
FRAGMENT = SUITES / "47_veldo_0107_ipc.py"
OUT = Path(__file__).resolve().parent / "driven.json"

FALSIFIERS = {
    "AC1": "ipc/the-coordinate-comes-from-the-request",
    "AC2": "ipc/transport-and-command-are-checked-separately",
    "AC3": "ipc/the-socket-follows-the-binding",
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
            if r["label"].startswith("VELDO-0107 %s " % ac):
                by_ac.setdefault(ac, {"rows": 0, "passed": 0, "driven": 0})
                by_ac[ac]["rows"] += 1
                by_ac[ac]["passed"] += int(r["passed"])
                by_ac[ac]["driven"] += int("DRIVEN" in r["label"])
    record = {
        "schema": "veldo.driven/v1",
        "spec_id": "VELDO-0107",
        "commit": commit,
        "taken_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fragment": str(FRAGMENT.relative_to(ROOT)),
        "fragment_sha256": hashlib.sha256(FRAGMENT.read_bytes()).hexdigest(),
        "description": ("One run of the spec's suite fragment with every row recorded. The rows run against TWO "
                        "REAL AUTHORITY CHILD PROCESSES on real AF_UNIX sockets, over two real enrolled git "
                        "clones, with each store's applied log compared after every call so a write to the "
                        "wrong store is visible rather than merely unasserted. Every DRIVEN row mutates a copy "
                        "of .veldo/control_client.py and requires the named row red while the unmutated copy "
                        "passes it. The last row is the negative control, and it compares a no-op copy against "
                        "THE ORIGINAL's answers in the same run rather than against literals, so it stays "
                        "green under every mutation of the organ: its one job is to show that copying changes "
                        "nothing. The signer is an HMAC the suite supplies, because the module holds no key "
                        "material. No model is called and nothing is spent."),
        "external_drives": [
            {"falsifier": "AC1 ipc/the-coordinate-comes-from-the-request",
             "mutation": ".veldo/control_client.py: the coordinate check drops the resolved store and keeps "
                         "only the comparison against the uuids the REQUEST declares, which is what a design "
                         "that believes the request's own labels looks like",
             "result": "AC1 RED, the other three rows pass"},
            {"falsifier": "AC2 ipc/transport-and-command-are-checked-separately",
             "mutation": ".veldo/control_client.py: the peer branch stops refusing, so a foreign uid falls "
                         "through to the signature check and a perfect signature carries it",
             "result": "AC2 RED, the other three rows pass"},
            {"falsifier": "AC3 ipc/the-socket-follows-the-binding",
             "mutation": ".veldo/control_client.py: socket_path_for prefers VELDO_CONTROL_SOCKET over the "
                         "address the binding implies",
             "result": "AC3 RED, the other three rows pass"},
        ],
        "suite_faults_the_drive_found": [
            "AC3 compared against a log snapshot taken before AC1's forgery, so AC1's mutant reddened AC3 as "
            "well: an accepted forgery added a row and the arithmetic moved. A falsifier that reds a row it "
            "was not pointed at is noise that reads like proof, so each row now counts from its own baseline.",
            "The negative control asserted LITERAL expected values, so it went red under every mutation of the "
            "organ, which made it a second copy of the other rows rather than a control. It now compares the "
            "no-op copy against the original's answers in the same run.",
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
