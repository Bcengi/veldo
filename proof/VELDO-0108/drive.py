#!/usr/bin/env python3
"""The VELDO-0108 driven record: run the spec's own suite fragment the way the dispatcher runs it
(shared.py's namespace, then the fragment), with `expect` recording every row instead of counting,
and write proof/VELDO-0108/driven.json.

The mutants are INSIDE the fragment: every DRIVEN row applies a mutation to a copy of the engine or
of the contract module, runs the same harness, and asserts the named row reds while the unmutated
copy passes it. So the record is the row list of one run, with the driven rows and the declared
falsifiers called out, plus the commit and the suite digest it was taken at. It runs nothing
detached, writes only this file, and is a record, never a gate claim: the gate is the gate.

  python3 proof/VELDO-0108/drive.py
"""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUITES = ROOT / "scripts" / "suites"
FRAGMENT = SUITES / "48_veldo_0108_relay.py"
OUT = Path(__file__).resolve().parent / "driven.json"

FALSIFIERS = {
    "AC1": "relay/the-authority-judges-not-the-relay",
    "AC2": "relay/ssh-is-transport-not-authority",
    "AC3": "relay/one-endpoint-one-judgement",
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
            if r["label"].startswith("VELDO-0108 %s " % ac):
                by_ac.setdefault(ac, {"rows": 0, "passed": 0, "driven": 0})
                by_ac[ac]["rows"] += 1
                by_ac[ac]["passed"] += int(r["passed"])
                by_ac[ac]["driven"] += int("DRIVEN" in r["label"])
    record = {
        "schema": "veldo.driven/v1",
        "spec_id": "VELDO-0108",
        "commit": commit,
        "taken_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fragment": str(FRAGMENT.relative_to(ROOT)),
        "fragment_sha256": hashlib.sha256(FRAGMENT.read_bytes()).hexdigest(),
        "description": ("One run of the spec's suite fragment with every row recorded. The relay is run as a "
                        "REAL CHILD PROCESS with the request on its standard input, exactly as sshd runs it, "
                        "against real authority child processes on real AF_UNIX sockets; its carrying promise "
                        "is measured separately against a bare echo socket, byte for byte. Every DRIVEN row "
                        "mutates a copy of .veldo/control_relay.py. The last row is the negative control and "
                        "it compares a no-op copy against THE ORIGINAL's answers in the same run rather than "
                        "against literals, so it stays green under every mutation. No model is called and "
                        "nothing is spent."),
        "stood_down_by_name": [
            "The leg where sshd authenticates the remote principal and refuses an unknown one is NOT "
            "exercised: there is no SSH server installed on this machine. That leg is sshd's, not this "
            "program's. Every decision this program makes is covered, including that SSH's own environment "
            "with a principal in it changes nothing about the answer."
        ],
        "external_drives": [
            {"falsifier": "AC1 relay/the-authority-judges-not-the-relay",
             "mutation": ".veldo/control_relay.py: the relay forwards the request but REPLACES the "
                         "authority's answer with an accepted one of its own. Deliberately sharper than a "
                         "relay that never connects: the command still reaches the authority, so the rest of "
                         "the fixture stays alive and the row turns on the answer rather than on everything "
                         "breaking at once",
             "result": "AC1 RED, and AC2 and AC3 with it: a relay that answers for the authority also makes "
                       "an unsigned command look accepted and makes the relayed answer differ from the local "
                       "one. Both are genuine consequences of the same mutation, not noise"},
            {"falsifier": "AC1, the carrying promise",
             "mutation": ".veldo/control_relay.py: forward() re-encodes what it carries through a lossy "
                         "utf-8 round trip, which is invisible on ordinary JSON and destroys a payload "
                         "containing bytes that are not valid utf-8",
             "result": "AC1 RED, the other four rows pass"},
            {"falsifier": "AC2 relay/ssh-is-transport-not-authority",
             "mutation": ".veldo/control_relay.py: the relay answers accepted whenever a principal is "
                         "present in the environment, which is the collapse of transport into authority",
             "result": "AC2 RED, the other four rows pass"},
            {"falsifier": "AC3 relay/one-endpoint-one-judgement",
             "mutation": ".veldo/control_relay.py: the endpoint is taken from VELDO_CONTROL_SOCKET instead "
                         "of the argument it was installed with",
             "result": "AC3 RED, and AC2 with it, because AC2 also asserts that the relay reads no "
                       "environment variable at all and this mutation makes it read one"},
        ],
        "suite_faults_the_drive_found": [
            "The echo-socket helper waited on accept() in a thread with no timeout, so a mutant that stopped "
            "the relay connecting hung the whole gate instead of reporting a red row. It now gives up and "
            "the row reads the timeout as a payload that never arrived, which is what it is.",
            "AC3 indexed the applied log at [-2] without checking its length, so a mutant that stopped the "
            "relay forwarding raised IndexError and killed the run mid-suite. An absent pair is now a failed "
            "comparison.",
            "The negative control asserted a LITERAL refusal reason, so it reddened under mutations instead "
            "of proving only that copying is neutral. It now compares against the original's answers.",
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
