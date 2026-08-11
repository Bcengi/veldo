#!/usr/bin/env python3
"""Runner catalog completeness check (BJ1 of PLAN-0003).

The runner suite is only trustworthy if every shipped runner carries its own
proof that it does not rubber-stamp: a passing fixture, a deliberately-failing
fixture, an honest status in the capability manifest, and a place in the gate
that actually drives it. This check ENUMERATES every runner directory under
engine/scripts/runners/ and fails closed on any runner that is
missing one of those four things.

Fails closed on purpose: a runner added later without a proving fixture pair,
without a capabilities entry, or without a gate wiring is caught here, so no
runner can ship uncatalogued or with a vacuous pass.

It also asserts BJ2 as a cheap mechanical property: the home gate never shells
a runner directly as a required check (a surface runner needs a product surface
the home repo lacks, so it is wired per adopting repo, never into this gate).

Stdlib only. Observes real files: it never trusts a name, it reads the tree,
the manifest, the selftest, and the gate catalog.

Exit 0 when every runner is complete and the gate shells no runner; 1 with the
findings named otherwise. Run standalone or via the repository self-test.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNNERS = ROOT / "engine" / "scripts" / "runners"
CAPS = ROOT / ".veldo" / "capabilities.yaml"
SELFTEST = ROOT / "scripts" / "selftest.py"
VERIFY = ROOT / "scripts" / "verify.sh"

# The capability manifest's own status vocabulary (see its header). A runner
# status outside this set, or blank, is a documentation bug the check catches.
STATUS_VOCAB = {"mechanical", "reference", "procedure", "absent", "control-plane"}


def _is_pass_fixture(name):
    n = name.lower()
    return n.startswith("pass") or n.startswith("good")


def _is_fail_fixture(name):
    n = name.lower()
    return n.startswith("fail") or n.startswith("bad")


def fixtures_of(runner_dir):
    """Every entry (file or subdirectory) under the runner's fixtures/ dir."""
    fx = runner_dir / "fixtures"
    if not fx.is_dir():
        return []
    return sorted(p.name for p in fx.iterdir())


def caps_entries_for(dirname, caps_text):
    """Statuses of every capability whose home points into runners/<dirname>/.

    The manifest writes each capability as a single-line flow mapping, so a
    per-line parse is exact and needs no yaml dependency.
    """
    statuses = []
    for line in caps_text.splitlines():
        if "home:" not in line or "runners/" not in line:
            continue
        home = re.search(r"home:\s*([^,}]+)", line)
        if not home:
            continue
        m = re.search(r"runners/([^/]+)/", home.group(1))
        if not m or m.group(1) != dirname:
            continue
        st = re.search(r"status:\s*([A-Za-z-]+)", line)
        statuses.append(st.group(1) if st else "")
    return statuses


def has_python_runner_module(runner_dir):
    """A Python runner module lives at the runner dir top level (not fixtures/).

    Its presence means the unit slot can import and drive the control logic in
    process, so such a runner MUST be referenced in the selftest.
    """
    return any(p.suffix == ".py" for p in runner_dir.iterdir() if p.is_file())


def has_test_wrapper(runner_dir):
    return any(p.name.startswith("test_") and p.suffix == ".sh"
               for p in runner_dir.iterdir() if p.is_file())


def audit(runners_dir=RUNNERS, caps_path=CAPS, selftest_path=SELFTEST):
    """Return a list of findings; empty means every runner is complete."""
    findings = []
    if not runners_dir.is_dir():
        return [f"runners directory missing: {runners_dir}"]
    caps_text = caps_path.read_text() if caps_path.is_file() else ""
    # THE UNIT SUITE IS A DIRECTORY NOW. WARP-0712 cut scripts/selftest.py into fragments
    # under scripts/suites/, so reading the entry point alone would read a dispatcher and
    # report every runner as unreferenced. The subject is unchanged: the whole unit suite.
    selftest_text = selftest_path.read_text() if selftest_path.is_file() else ""
    _suites = selftest_path.parent / "suites"
    if _suites.is_dir():
        selftest_text += "".join(f.read_text() for f in sorted(_suites.glob("*.py")))

    runner_dirs = sorted(p for p in runners_dir.iterdir() if p.is_dir())
    if not runner_dirs:
        return ["no runner directories found (suite is empty)"]

    for d in runner_dirs:
        name = d.name
        fx = fixtures_of(d)

        if not any(_is_pass_fixture(f) for f in fx):
            findings.append(f"{name}: no passing fixture (pass*/good* under fixtures/)")
        if not any(_is_fail_fixture(f) for f in fx):
            findings.append(f"{name}: no deliberately-failing fixture (fail*/bad* under fixtures/)")

        statuses = caps_entries_for(name, caps_text)
        if not statuses:
            findings.append(f"{name}: no capabilities.yaml entry (home under runners/{name}/)")
        else:
            for st in statuses:
                if not st:
                    findings.append(f"{name}: capabilities entry has a blank status")
                elif st not in STATUS_VOCAB:
                    findings.append(f"{name}: capabilities status '{st}' not in the vocabulary "
                                    f"({sorted(STATUS_VOCAB)})")

        referenced = f"runners/{name}/" in selftest_text
        py = has_python_runner_module(d)
        wrapper = has_test_wrapper(d)
        if py and not referenced:
            findings.append(f"{name}: Python runner module not referenced in scripts/selftest.py "
                            f"(the unit slot must drive its control logic)")
        if not referenced and not wrapper:
            findings.append(f"{name}: not exercised by the gate (no selftest reference and no "
                            f"fixture-driving test_*.sh wrapper)")

    return findings


def gate_shells_a_runner(verify_path=VERIFY):
    """BJ2: names any required gate command that shells a runner directly.

    The home gate's required checks must not invoke a runner (a surface runner
    needs a backend, emulator, or third party the home repo lacks). The unit
    slot imports runner control logic in process with stdlib only, which is not
    shelling a live surface, so this looks only at required: gate commands.
    """
    offenders = []
    if not verify_path.is_file():
        return ["verify.sh missing"]
    for line in verify_path.read_text().splitlines():
        m = re.match(r"\s*CHECK_\w+=\"required:(.*)\"", line)
        if m and "runners/" in m.group(1):
            offenders.append(line.strip())
    return offenders


def main():
    findings = audit()
    offenders = gate_shells_a_runner()
    total = len(list((RUNNERS).iterdir())) if RUNNERS.is_dir() else 0
    if findings:
        print("runner catalog: INCOMPLETE")
        for f in findings:
            print(f"   - {f}")
    if offenders:
        print("runner catalog: gate shells a surface runner as a required check (BJ2 violation)")
        for o in offenders:
            print(f"   - {o}")
    if findings or offenders:
        print("runner catalog: FAIL")
        return 1
    print(f"runner catalog: pass ({total} runners, each with a fixture pair, an honest "
          f"capabilities status, and a gate wiring; no runner shelled by the gate)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
