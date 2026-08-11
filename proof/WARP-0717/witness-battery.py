#!/usr/bin/env python3
"""WARP-0717's failing-witness battery, regenerated for review 1's correction C1.

For every guard this item adds, the mutation that makes it RED, and for every mutation the
evidence that it APPLIED: the substitution count and the sha256 of each touched file before,
after and restored. Review 1's finding was that the previous artifact CLAIMED those fields
and did not carry them, which made the battery's strongest property unauditable from the
record: that a mutation which failed to apply is reported NOT_APPLIED rather than as a guard
that held.

Usage: witness_battery.py <source-repo> <work-dir> <out.json>

The work dir is an ABSOLUTE path; the repository is COPIED there and every mutation is applied
to the copy. The source tree is never written.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

SRC, WORK, OUT = Path(sys.argv[1]).resolve(), Path(sys.argv[2]), Path(sys.argv[3])
assert str(WORK).startswith("/tmp/"), "the work dir must be an absolute path under /tmp"

TARGET = "14_warp_0717_subset_runner"
SELFTEST = "scripts/selftest.py"
RUNSCOPE = "scripts/run_scope.py"
FRAG14 = "scripts/suites/14_warp_0717_subset_runner.py"
MANIFEST = "scripts/suites/manifest.json"
REQUIRES = "scripts/suites/requires.json"
VERIFY = "scripts/verify.sh"
PACKS = ".warp/packs.json"


def sub(path, old, new, count=1):
    return {"kind": "substitute", "path": path, "old": old, "new": new, "count": count}


def create(path, text):
    return {"kind": "create", "path": path, "text": text}


NEW_FRAGMENT = 'expect("m14 the fifteenth fragment", True)\n'

MUTATIONS = [
    ("M1 aggregate_line stops consulting the scope",
     [sub(RUNSCOPE, '        self._refuse("emit the aggregate summary line")\n', "")]),
    ("M2 verify_stamp_payload stops refusing",
     [sub(RUNSCOPE, '        self._refuse("write the verify stamp (.warp/last_verify)")\n', "")]),
    ("M3 unit_evidence_check stops refusing",
     [sub(RUNSCOPE, '        self._refuse("satisfy the required-evidence check")\n', "")]),
    ("M4 a partial run exits 0 when nothing failed",
     [sub(RUNSCOPE, "            return PARTIAL_FAILED_EXIT if failed else PARTIAL_PASSED_EXIT",
          "            return PARTIAL_FAILED_EXIT if failed else 0")]),
    ("M5 partiality is decided by the count of suites, not by the selector",
     [sub(RUNSCOPE, "        return self.selector is not None",
          "        return len(self.running) < len(self.declared)")]),
    ("M6 an unknown selector exits 0 instead of refusing",
     [sub(SELFTEST, '        print("selftest: %s" % e)\n        sys.exit(2)',
          '        print("selftest: %s" % e)\n        sys.exit(0)')]),
    ("M7 resolve accepts a PREFIX of a real suite name",
     [sub(RUNSCOPE, "    for name in asked:\n        if name not in names:",
          "    asked = [([n for n in names if n.startswith(name)] or [name])[0]\n"
          "             for name in asked]\n"
          "    for name in asked:\n        if name not in names:")]),
    ("M8 the closure loses its fixpoint step (the generator returns the direct demand)",
     [sub(RUNSCOPE, "    return transitive_close(direct_demand(manifest, measurement))",
          "    return direct_demand(manifest, measurement)")]),
    ("M9 the gate's unit slot grows a selector",
     [sub(VERIFY, 'CHECK_unit="required:python3 scripts/selftest.py"',
          'CHECK_unit="required:python3 scripts/selftest.py --suite %s"' % TARGET)]),
    ("M10 the partial line drops its elapsed time",
     [sub(RUNSCOPE,
          '        return ("selftest (PARTIAL, %d of %d suites): %d passed, %d failed in %.2fs"\n'
          "                % (len(self.running), len(self.declared), passed, failed, elapsed_s))",
          '        return ("selftest (PARTIAL, %d of %d suites): %d passed, %d failed"\n'
          "                % (len(self.running), len(self.declared), passed, failed))")]),
    ("M11 the banner stops naming itself a partial run",
     [sub(RUNSCOPE,
          '            "PARTIAL RUN OF THE UNIT SUITE. THIS IS NOT VERIFICATION AND CANNOT '
          'BECOME IT.",',
          '            "a run of the unit suite.",')]),
    ("M11b the banner drops the separator the run-list parse looks for (the shape that "
     "used to CRASH the battery instead of reddening it)",
     [sub(RUNSCOPE, '            "  running     %d of %d suites: %s" %',
          '            "  running     %d of %d fragments %s" %')]),
    ("M12 the stamp payload drops a key verify.sh writes",
     [sub(RUNSCOPE, '                "checks_run": checks_run, "checks_na": checks_na}',
          '                "checks_run": checks_run}')]),
    ("M13 the derived closure table loses a fragment the manifest enumerates",
     [sub(REQUIRES, '  "05_tracker_routing_resolver_warp": [\n'
                    '   "05_tracker_routing_resolver_warp"\n'
                    "  ],\n", "")]),
    ("M14 ADDITIVE CONTROL: a fifteenth fragment with neither a measured region range nor a "
     "declared requires",
     [sub(MANIFEST, '  {\n   "name": "14_warp_0717_subset_runner",',
          '  {\n   "name": "15_m14_additive_control",\n'
          '   "file": "15_m14_additive_control.py",\n'
          '   "regions": "none"\n  },\n'
          '  {\n   "name": "14_warp_0717_subset_runner",'),
      create("scripts/suites/15_m14_additive_control.py", NEW_FRAGMENT)]),
    ("M15 the unrecognised-flag refusal stops exiting 2 (it exits 0, the way the "
     "unrecognised flag itself used to)",
     [sub(SELFTEST, '             ", ".join(sorted(FLAGS))))\n    sys.exit(2)',
          '             ", ".join(sorted(FLAGS))))\n    sys.exit(0)')]),
    ("M15b the unrecognised-flag refusal stops naming itself",
     [sub(SELFTEST, 'UNRECOGNISED_FLAG = "UNRECOGNISED_FLAG"',
          'UNRECOGNISED_FLAG = "unknown option"')]),
    ("M16 EMPTIED SOURCE: the hostile-selector shape list, which two bound all()s iterate",
     [sub(FRAG14, "_w17_hostile_runs = []\n",
          "_W17_HOSTILE = []\n_w17_hostile_runs = []\n")]),
    ("M17 EMPTIED SOURCE: the literal file pair the canon-absence probe list is built from",
     [sub(FRAG14, '_W17_CANON_FILES = ("selftest.py", "run_scope.py")',
          "_W17_CANON_FILES = ()")]),
    ("M18 EMPTIED SOURCE: the declared pack roster the canon-absence assertion reads",
     [sub(PACKS, '"packs": [', '"packs": [], "packs_moved_aside": [', 1)]),
    ("M19 EMPTIED SOURCE: the bad-flag shape list the flag-refusal all() iterates",
     [sub(FRAG14, "_w17_flag_runs = [(_label, _arg)",
          "_W17_BAD_FLAGS = []\n_w17_flag_runs = [(_label, _arg)")]),
    ("MX NEGATIVE CONTROL OF THE BATTERY ITSELF: a mutation whose anchor is not in the file "
     "at all. It must be reported NOT_APPLIED, never as a guard that held, and the record "
     "must show the count that refused it",
     [sub(RUNSCOPE, "        self._refuse(\"an act no version of this module ever had\")\n",
          "        pass\n")]),
]
CONTROL_PREFIX = "MX"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest() if Path(p).exists() else "ABSENT"


def run_target(root):
    t = time.monotonic()
    r = subprocess.run([sys.executable, "scripts/selftest.py", "--suite", TARGET],
                       capture_output=True, text=True, cwd=str(root))
    out = r.stdout + r.stderr
    return r.returncode, out, time.monotonic() - t


PARTIAL_RE = re.compile(r"^selftest \(PARTIAL, \d+ of \d+ suites\): (\d+) passed, (\d+) failed",
                        re.M)


def classify(rc, out):
    """RED, GREEN or CRASH, from the run's own verdict line.

    A run with NO verdict line is a CRASH and is never counted as a caught defect: a dead run
    prints nothing and reads like a run that found nothing wrong, which is worse than a red.
    """
    m = PARTIAL_RE.search(out)
    if not m:
        return "CRASH", None, None
    return ("RED" if int(m.group(2)) else "GREEN"), int(m.group(1)), int(m.group(2))


def failed_labels(out):
    return [ln.split("SELFTEST FAIL:", 1)[1].strip()
            for ln in out.splitlines() if "SELFTEST FAIL:" in ln]


def main():
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    root = WORK / "repo"
    shutil.copytree(SRC, root, ignore=shutil.ignore_patterns(".git", "__pycache__"))

    rc, out, el = run_target(root)
    verdict, passed, failed = classify(rc, out)
    baseline = {"verdict": "GREEN" if verdict == "GREEN" else verdict,
                "passed": passed, "failed": failed, "exit": rc, "elapsed_s": round(el, 2)}
    print("baseline: %s %s passed %s failed exit=%s %.2fs"
          % (verdict, passed, failed, rc, el))
    if verdict != "GREEN":
        print(out[-4000:])
        raise SystemExit("the baseline is not GREEN; the battery would be meaningless")

    witnesses = []
    for name, ops in MUTATIONS:
        files, applied, why = [], True, ""
        for op in ops:
            p = root / op["path"]
            before = sha(p)
            rec = {"path": op["path"], "op": op["kind"], "sha256_before": before}
            if op["kind"] == "substitute":
                text = p.read_text()
                n = text.count(op["old"])
                rec["substitutions"] = n
                rec["substitutions_expected"] = op["count"]
                if n != op["count"]:
                    applied, why = False, ("expected %d substitution(s) of the anchor in %s, "
                                           "found %d" % (op["count"], op["path"], n))
                    rec["sha256_after"] = before
                    files.append(rec)
                    break
                p.write_text(text.replace(op["old"], op["new"]))
            else:
                rec["substitutions"] = 1
                rec["substitutions_expected"] = 1
                if p.exists():
                    applied, why = False, "%s already exists; the create op is not additive" % op["path"]
                    rec["sha256_after"] = before
                    files.append(rec)
                    break
                p.write_text(op["text"])
            rec["sha256_after"] = sha(p)
            if rec["sha256_after"] == before:
                applied, why = False, "the sha256 of %s did not change" % op["path"]
                files.append(rec)
                break
            files.append(rec)

        if applied:
            rc, out, el = run_target(root)
            verdict, passed, failed = classify(rc, out)
            labels = failed_labels(out)
        else:
            verdict, passed, failed, labels, rc, el = "NOT_APPLIED", None, None, [], None, 0.0
            out = ""

        # Restore, then ASSERT the restoration, before the next mutation runs at all.
        for op, rec in zip(ops, files):
            p = root / op["path"]
            if op["kind"] == "create":
                if p.exists():
                    p.unlink()
            else:
                src = SRC / op["path"]
                shutil.copy(src, p)
            rec["sha256_restored"] = sha(p)
            rec["restored_ok"] = rec["sha256_restored"] == rec["sha256_before"]
        for rec in files:
            if not rec.get("restored_ok"):
                raise SystemExit("RESTORATION FAILED for %s after %s" % (rec["path"], name))

        w = {"mutation": name, "verdict": verdict,
             "applied": applied,
             "is_battery_control": name.startswith(CONTROL_PREFIX),
             "files": files,
             "exit": rc,
             "passed": passed, "failed": failed,
             "failed_assertions": len(labels),
             "detail": "; ".join(lab[:100] for lab in labels[:4])}
        if not applied:
            w["not_applied_because"] = why
        witnesses.append(w)
        print("%-8s %-9s failed=%-3s exit=%-4s %.2fs  %s"
              % (name.split()[0], verdict, failed, rc, el, name[:70]))

    # The battery's own negative control: with NOTHING mutated, the target must be GREEN
    # again at the end, which is what proves every restoration above put the tree back.
    rc, out, el = run_target(root)
    verdict, passed, failed = classify(rc, out)
    closing = {"verdict": verdict, "passed": passed, "failed": failed, "exit": rc}
    print("closing baseline: %s %s passed %s failed exit=%s" % (verdict, passed, failed, rc))

    guards = [w for w in witnesses if not w["is_battery_control"]]
    controls = [w for w in witnesses if w["is_battery_control"]]
    counts = {}
    for w in guards:
        counts[w["verdict"]] = counts.get(w["verdict"], 0) + 1
    for k in ("RED", "GREEN", "CRASH", "NOT_APPLIED"):
        counts.setdefault(k, 0)
    doc = {
        "schema": "warp.measurement/v1",
        "spec_id": "WARP-0717",
        "what": "For every guard this item adds, the mutation that makes it RED. A guard with "
                "no failing witness is a description of a property, not a check on it.",
        "regenerated": "REGENERATED for review 1's correction C1. The previous version of this "
                       "file claimed a substitution count and the sha256 before, after and "
                       "restored, and carried none of them, so the property that makes the "
                       "battery trustworthy - that a mutation which failed to apply is "
                       "reported NOT_APPLIED rather than as a guard that held - could not be "
                       "audited from the record. Every witness now carries them per touched "
                       "file. The protocol was followed the first time; the record did not "
                       "show it, and the remedy for that is to make the record show it.",
        "method": [
            "ONE copy of the repository at an absolute path under /tmp, never the worktree; "
            ".git and __pycache__ excluded from the copy.",
            "per mutation, per touched file: sha256 BEFORE, count the anchor's occurrences and "
            "ASSERT the count is the expected one, apply, ASSERT the sha256 CHANGED, run, "
            "restore from the source tree, ASSERT the sha256 is back to the BEFORE value. A "
            "mutation whose anchor count is wrong or whose sha256 did not move is reported "
            "NOT_APPLIED, never as a guard that held.",
            "a `create` op has no BEFORE bytes, so its sha256_before and sha256_restored are "
            "the literal ABSENT and its APPLIED evidence is that the file did not exist and "
            "then did.",
            "the observation is fragment 14 alone via `--suite 14_warp_0717_subset_runner`, "
            "about 2s, so the battery costs a minute rather than 20 full runs.",
            "verdict is read from the run's OWN partial verdict line. A run with no verdict "
            "line is CRASH, not RED: a dead run prints nothing and reads like a run that "
            "found nothing wrong, which this repository calls worse than a red.",
            "the battery ends by re-running the unmutated target, so the closing baseline is "
            "the proof that every restoration put the tree back.",
        ],
        "result": "%d of %d guard mutations RED, %d GREEN, %d CRASH, %d NOT_APPLIED"
                  % (counts["RED"], len(guards), counts["GREEN"], counts["CRASH"],
                     counts["NOT_APPLIED"]),
        "battery_negative_control": "%d control mutation(s) with an anchor that is not in the "
                                    "file: %s. Without this the NOT_APPLIED classification is "
                                    "a claim the record never exercises."
                                    % (len(controls),
                                       ", ".join("%s -> %s" % (w["mutation"].split(":")[0],
                                                               w["verdict"])
                                                 for w in controls)),
        "baseline": baseline,
        "closing_baseline": closing,
        "witnesses": witnesses,
    }
    OUT.write_text(json.dumps(doc, indent=1) + "\n")
    print("wrote %s" % OUT)


main()
