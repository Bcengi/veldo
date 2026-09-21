#!/usr/bin/env python3
"""The VELDO-0109 driven record: run the spec's own suite fragment the way the dispatcher runs it
(shared.py's namespace, then the fragment), with `expect` recording every row instead of counting,
and write proof/VELDO-0109/driven.json.

The mutants are INSIDE the fragment: every DRIVEN row applies a mutation to a copy of the engine or
of the contract module, runs the same harness, and asserts the named row reds while the unmutated
copy passes it. So the record is the row list of one run, with the driven rows and the declared
falsifiers called out, plus the commit and the suite digest it was taken at. It runs nothing
detached, writes only this file, and is a record, never a gate claim: the gate is the gate.

  python3 proof/VELDO-0109/drive.py
"""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUITES = ROOT / "scripts" / "suites"
FRAGMENT = SUITES / "49_veldo_0109_unavailable.py"
OUT = Path(__file__).resolve().parent / "driven.json"

FALSIFIERS = {
    "AC1": "unavailable/no-local-authority-appears",
    "AC2": "unavailable/a-stale-read-says-so",
    "AC3": "unavailable/no-client-starts-the-authority",
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
            if r["label"].startswith("VELDO-0109 %s " % ac):
                by_ac.setdefault(ac, {"rows": 0, "passed": 0, "driven": 0})
                by_ac[ac]["rows"] += 1
                by_ac[ac]["passed"] += int(r["passed"])
                by_ac[ac]["driven"] += int("DRIVEN" in r["label"])
    record = {
        "schema": "veldo.driven/v1",
        "spec_id": "VELDO-0109",
        "commit": commit,
        "taken_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fragment": str(FRAGMENT.relative_to(ROOT)),
        "fragment_sha256": hashlib.sha256(FRAGMENT.read_bytes()).hexdigest(),
        "description": ("One run of the spec's suite fragment with every row recorded, against a real "
                        "authority child process on a real AF_UNIX socket that is then STOPPED. Every DRIVEN "
                        "row mutates a copy of .veldo/control_client.py. The last row is the negative control "
                        "and compares a no-op copy against THE ORIGINAL's answers in the same run. No model "
                        "is called and nothing is spent."),
        "how_nothing_appeared_is_asked": [
            "NEW files only, in BOTH directories a fallback could write into: the authority's, and the "
            "clone's own control directory where the last-seen record lives. Comparing a whole listing "
            "measures the SHUTDOWN, because the socket file disappears with the authority.",
            "The kernel, not a string. /proc/net/unix is asked whether anything is bound at the address, "
            "because a process census matched by name matches the command doing the matching: the first "
            "version of that check found its own shell, whose command line contained the word it was "
            "searching for.",
        ],
        "external_drives": [
            {"falsifier": "AC1 unavailable/no-local-authority-appears",
             "mutation": ".veldo/control_client.py: send() answers from the last-seen record instead of "
                         "refusing, reporting the command applied locally",
             "result": "AC1 RED, and AC2 with it, because a fallback also makes inspect() see an accepted "
                       "response and report stale false. A genuine consequence of the same mutation"},
            {"falsifier": "AC1, the refusal's naming",
             "mutation": ".veldo/control_client.py: the refusal stops carrying the service it could not "
                         "reach",
             "result": "AC1 RED, and AC2 with it, because the stale answer takes its service from that same "
                       "refusal"},
            {"falsifier": "AC2 unavailable/a-stale-read-says-so",
             "mutation": ".veldo/control_client.py: a stale answer reports stale false",
             "result": "AC2 RED, the other three rows pass"},
        ],
        "design_faults_found_before_landing": [
            "The last-seen record was first written BESIDE THE STORE. That is wrong in exactly the case this "
            "package exists for: the store lives on the authority's machine, so a remote clone reaching it "
            "through the SSH relay cannot write there and should not. It is the clone's knowledge, not a "
            "fact about the store, and putting it there made a client a writer into the authority's own "
            "directory. It now lives in the clone's own control directory beside its enrollment binding.",
            "A comment claimed the record is read-only by construction and that send never touches it. False: "
            "send reads it inside the unavailable branch to put the watermark in the refusal. It is read to "
            "DESCRIBE a failure and never to decide one, and the row asserts the behaviour rather than the "
            "easier source-level claim that would have been a lie.",
        ],
        "suite_faults_the_drive_found": [
            "The negative control compared the refusal's .reason attribute directly and CRASHED under the "
            "fallback mutant, whose copy answers with a mapping rather than raising. A control that raises "
            "instead of reporting tells a reader nothing about whether copying changed anything; it is now "
            "shape-agnostic.",
            "A mutant handle was the organ's DIRECTORY rather than the module, which raised an "
            "AttributeError deep inside a helper instead of reddening a row.",
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
