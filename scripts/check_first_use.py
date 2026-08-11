#!/usr/bin/env python3
"""FIRST USE: no suite may pin this repository's current emptiness as a required invariant.

WHAT WENT WRONG, AND IT WAS ONE SHAPE IN FIVE PLACES RATHER THAN FIVE BUGS. Several assertions
are written as MEASURED OVER THIS REPOSITORY and what they actually measure is that nobody has
used the estimation layer YET. Today's emptiness becomes a required invariant, so the suite stays
green exactly as long as the feature goes unused and reddens the moment somebody uses it. Proven
in a throwaway copy of this repository: baseline 4145 passed 0 failed; after ONE sanctioned
`.veldo/spend.py record` the same suite is 4141 passed 4 FAILED. A gate that breaks on first real
use is worse than a missing check, because the person who hits it is whoever first tries the
feature, and what it teaches them is that the gate is noise.

THE SHAPE THAT IS ALLOWED. An assertion measured over the live repository MAY require the honest
stand-down when nothing is recorded, and the range or measured branch when something IS recorded,
with the branch chosen by what it just measured. What it must never do is ASSERT that the measured
set is empty. The partition and the structural invariants stay unconditional; only the arm that
depends on there being no data becomes conditional. This check refuses the first shape and accepts
the second, and it does so by measuring the property rather than a spelling of it.

WHY THIS IS BEHAVIOURAL AND NOT A GREP, stated plainly because the alternative was considered and
rejected. Statically, `pins emptiness` and `branches on emptiness` are the same tokens in a
different control-flow position: `x == 0` inside a condition and `x == 0` inside an `if` are one
comparison, and the difference lives in the enclosing flow, through helper calls, across the one
shared namespace these fragments execute in (scripts/suites/manifest.json), and behind labels
composed at runtime. A tree-walk could approximate it, would be wrong in both directions, and
would be evadable by anybody who read it. So this check does the thing itself: it copies the
repository, uses the sanctioned writer the way the layer exists to be used, runs the whole suite
over the result, and requires that NO assertion that passed before now fails. That is the property
in one sentence and there is no spelling of the defect that survives it.

WHAT IT COSTS AND WHY IT STILL BELONGS IN THE GATE. One nested full selftest, measured at about
90 seconds, plus two tree copies of about a second. The BASELINE run is LAZY: it happens only when
the mutated run reports a failure, because with zero failures there is nothing to attribute. So
the green path pays ONE nested run and the second run is paid only when the gate is about to be red
anyway. That is why this sits in the `integration` slot of scripts/verify.sh, which was
`na:no separate integration suite yet` and is now the one check in this repository that drives a
sanctioned writer end to end and reads the whole suite's verdict over the result.

WHY BOTH TREES ARE COPIES, including the untouched one. Other lanes edit scripts/suites/ while this
runs. Copying the pristine tree ONCE and then copying THAT copy makes the two trees byte-identical
by construction, so a regression can never be an artefact of the live tree changing between two
reads. It also cancels any sensitivity to the tree's location, since both runs see the same kind of
path.

WHAT THIS CHECK CANNOT SEE, on record because a check whose limits are undocumented is the thing
it is fixing:
  1. IT ONLY FILLS THE CORPORA ITS MUTATION TABLE FILLS. Today that is recorded spend, through
     .veldo/spend.py, covering all three declared spend fields. A suite that pins the emptiness of
     some OTHER live set stays invisible here. The known example is the gate-event half of
     WARP-1409 AC4: `gate_event_records == 0` is pinned because no gate.passed event in this
     repository carries a spec id, and no sanctioned writer emits one, so there is nothing honest
     to drive. When a writer for it exists, the fix is A NEW ENTRY IN `MUTATIONS`, never a pattern
     match. That is the extension rule and it is the whole design.
  2. IT CANNOT SEE A PIN ON A SMALL NONZERO COUNT. The mutation records spend for TWO specs, so
     `== 0` and `== 1` pins both fall, but an assertion requiring `spend_events < 5` would survive
     until the table records more.
  3. IT MEASURES THE SUITE, NOT THE MODULES. A module that itself hardcodes today's emptiness but
     is asserted only through fixtures reddens nothing here.
  4. IT CANNOT ATTRIBUTE A PRE-EXISTING FAILURE. When the tree is already red, this check reports
     the pre-existing set and passes on it: the `unit` slot owns those, and reporting them twice
     as though this mutation caused them would be the false accusation this check exists to avoid.

FAILING LOUD IS NOT OPTIONAL. Every way this check can fail to answer exits NONZERO with the reason
named: no interpreter, a missing writer or dispatcher, a copy that did not complete, a writer that
exited nonzero, a mutation that did not observably land, a run that produced no summary line, or a
summary whose failure count disagrees with the failure names it printed. A check that passed by
default on its own inability would be a worse version of the defect it refuses.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELFTEST = ROOT / "scripts" / "selftest.py"
SUITES = ROOT / "scripts" / "suites"
EVENT_LOG = Path(".veldo") / "events.jsonl"
SPEND_FIELDS = ("tokens", "cost_usd", "human_minutes")
SUMMARY_PREFIX = "selftest:"
FAIL_MARK = "SELFTEST FAIL:"
RUN_TIMEOUT_S = 1800
WRITE_TIMEOUT_S = 120
TMP_PREFIX = "veldo-first-use-"

# THE MUTATION TABLE: the sanctioned first uses of a layer whose corpus is empty today. One entry
# is one FAMILY and costs one nested suite run; the writes inside an entry are applied to the SAME
# tree, because they are one story ("somebody started recording spend") and one run answers for all
# of them. Every write must be a use the layer EXISTS FOR, invoked through the sanctioned CLI and
# never by writing the store directly: a mutation that reached past the writer would prove nothing
# about what happens when a person uses the feature.
#
# THE SPEC IDS ARE REAL SPECS OF THIS CORPUS. A synthetic id would be a use nobody will ever make,
# and two of the assertions this catches read the spec's own record.
MUTATIONS = [
    {
        "family": "spend_recorded",
        "why": "somebody used .veldo/spend.py, which is the whole point of the estimation layer: "
               "a token count is not derivable from inside the repository, so a record is the only "
               "way the corpus is ever nonempty",
        "writer": Path(".veldo") / "spend.py",
        "writes": [
            ["record", "--spec", "WARP-0100", "--basis", "harness_reported", "--tokens", "750000"],
            ["record", "--spec", "WARP-1401", "--basis", "agent_estimate", "--cost-usd", "42.5",
             "--human-minutes", "35"],
        ],
        # WHAT COUNTS AS THE MUTATION HAVING LANDED, measured over the store the layer reads rather
        # than trusted from the writer's exit code. ONE enumeration, used for both the before and
        # the after number, because two enumerations of one set diverge.
        "probe": "events in .veldo/events.jsonl carrying tokens, cost_usd or human_minutes",
    },
]


class CannotAnswer(Exception):
    """This check could not measure its property. Always nonzero, never a pass."""


def _spend_carrying(tree):
    """(events carrying a spend field, lines that did not parse) in one pass over the log.

    An unparsable line is REPORTED and not fatal: the log is append-only with several producers,
    and the before/after comparison this feeds is unaffected by a line neither read can parse.
    A MISSING log is fatal, because then the probe cannot answer at all."""
    path = tree / EVENT_LOG
    if not path.exists():
        raise CannotAnswer("no %s in %s: the store this check probes is absent" % (EVENT_LOG, tree))
    n, bad = 0, 0
    for line in path.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            bad += 1
            continue
        if not isinstance(ev, dict):
            bad += 1
            continue
        if any(isinstance(ev.get(f), (int, float)) and not isinstance(ev.get(f), bool)
               for f in SPEND_FIELDS):
            n += 1
    return n, bad


def _copy(src, dest, what):
    try:
        shutil.copytree(src, dest, symlinks=True)
    except (OSError, shutil.Error) as e:
        raise CannotAnswer("could not build the %s tree at %s: %s" % (what, dest, e))
    if not (dest / "scripts" / "selftest.py").exists():
        raise CannotAnswer("the %s tree at %s has no scripts/selftest.py: the copy is incomplete"
                           % (what, dest))
    return dest


def _child_env():
    """The environment a nested run gets. VELDO_SUITE_ORDER is dropped because an inherited
    diagnostic ordering would silently change what this measurement ran."""
    env = dict(os.environ)
    env.pop("VELDO_SUITE_ORDER", None)
    return env


def _run_suite(tree, label):
    """(passed, failed, [failure names]) from one full nested run, or CannotAnswer.

    THE FAILURE NAMES AND THE FAILURE COUNT COME FROM DIFFERENT LINES OF THE SAME OUTPUT, so they
    are asserted EQUAL rather than assumed to agree. They disagree when a suite crashes partway,
    when output is truncated, or when a fragment prints its own lookalike line, and in every one of
    those cases this check does not know what it measured and says so."""
    t0 = time.monotonic()
    try:
        proc = subprocess.run([sys.executable, "scripts/selftest.py"], cwd=str(tree),
                              capture_output=True, text=True, env=_child_env(),
                              timeout=RUN_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        raise CannotAnswer("the %s run did not finish inside %ds" % (label, RUN_TIMEOUT_S))
    except OSError as e:
        raise CannotAnswer("could not run the %s suite: %s" % (label, e))
    out = proc.stdout + proc.stderr
    names = [ln.split(FAIL_MARK, 1)[1].strip() for ln in out.splitlines() if FAIL_MARK in ln]
    summary = [ln for ln in out.splitlines() if ln.startswith(SUMMARY_PREFIX) and "passed," in ln]
    if len(summary) != 1:
        raise CannotAnswer("the %s run produced %d summary lines, expected exactly 1; its exit was "
                           "%d and its last output line was %r. Without the summary this check "
                           "cannot tell a clean run from a crash"
                           % (label, len(summary), proc.returncode,
                              (out.splitlines() or [""])[-1][:200]))
    try:
        words = summary[0].replace(",", " ").split()
        passed = int(words[words.index("passed") - 1])
        failed = int(words[words.index("failed") - 1])
    except (ValueError, IndexError):
        raise CannotAnswer("could not read counts from the %s summary line %r"
                           % (label, summary[0][:200]))
    if len(names) != failed:
        raise CannotAnswer("the %s run printed %d failure names and a summary saying %d failed. "
                           "These are one set counted twice and they disagree, so this check does "
                           "not know what failed" % (label, len(names), failed))
    print("   %s run: %d passed, %d failed (%.0fs)" % (label, passed, failed,
                                                       time.monotonic() - t0), flush=True)
    return passed, failed, names


def _locate(name):
    """`file:line` of the assertion carrying this label, or a stated inability.

    A label is a concatenation of source lines and some are composed at runtime with `%`, so the
    longest contiguous prefix is tried first and shorter ones after. This is a convenience for the
    reader: not finding it never changes the verdict and is never silent."""
    for width in (90, 60, 40, 24):
        needle = name[:width]
        if len(needle) < width:
            continue
        for path in sorted(SUITES.glob("*.py")):
            try:
                lines = path.read_text(errors="replace").splitlines()
            except OSError:
                continue
            for i, line in enumerate(lines, 1):
                if needle in line:
                    return "%s:%d" % (path.relative_to(ROOT), i)
    return "location not resolved in scripts/suites (this label is composed at runtime)"


def _apply(tree, mut):
    """Apply one family's writes through the sanctioned writer, and PROVE the store changed."""
    writer = tree / mut["writer"]
    if not writer.exists():
        raise CannotAnswer("the sanctioned writer %s does not exist: this check cannot use the "
                           "layer the way a person would" % mut["writer"])
    before, bad_before = _spend_carrying(tree)
    for argv in mut["writes"]:
        try:
            proc = subprocess.run([sys.executable, str(mut["writer"])] + argv, cwd=str(tree),
                                  capture_output=True, text=True, env=_child_env(),
                                  timeout=WRITE_TIMEOUT_S)
        except (subprocess.TimeoutExpired, OSError) as e:
            raise CannotAnswer("the sanctioned writer could not be driven: %s %s: %s"
                               % (mut["writer"], " ".join(argv), e))
        if proc.returncode != 0:
            raise CannotAnswer("the sanctioned writer refused a legitimate use: %s %s exited %d "
                               "saying %r" % (mut["writer"], " ".join(argv), proc.returncode,
                                              (proc.stderr or proc.stdout).strip()[:300]))
    after, bad_after = _spend_carrying(tree)
    if after <= before:
        raise CannotAnswer("the mutation did not land: %s went from %d to %d after %d sanctioned "
                           "writes that all exited 0. This check measures what happens once the "
                           "corpus is nonempty, so it has measured nothing"
                           % (mut["probe"], before, after, len(mut["writes"])))
    print("   mutation applied: %s went %d -> %d (%d writes through %s)"
          % (mut["probe"], before, after, len(mut["writes"]), mut["writer"]), flush=True)
    if bad_before or bad_after:
        print("   note: %d/%d log lines did not parse (counted in neither number)"
              % (bad_before, bad_after), flush=True)
    return before, after


def _rmtree(path):
    """Remove the temporary ROOT this check created, by an absolute path it built, or refuse.

    Two conditions, both required: the directory NAME carries this check's prefix and the path
    lives under the system temporary directory. A destructive call that took its target from
    anywhere less specific than that does not belong in a gate check."""
    p = Path(path).resolve()
    if p.name.startswith(TMP_PREFIX) and str(p).startswith(str(Path(tempfile.gettempdir()))):
        shutil.rmtree(p, ignore_errors=True)
    else:
        print("   refusing to remove %s: not a tree this check created" % p, flush=True)


def main(argv):
    keep = "--keep" in argv
    unknown = [a for a in argv if a.startswith("--") and a != "--keep"]
    if unknown:
        print("check_first_use: UNRECOGNISED_FLAG: %s. This check recognises exactly --keep "
              "(retain the temporary trees for inspection). Refusing rather than ignoring it."
              % ", ".join(repr(a) for a in unknown))
        return 2

    print("== first use: no suite may require this repository's current emptiness", flush=True)
    t0 = time.monotonic()
    tmproot = None
    verdict_red = []
    notes = []
    try:
        if not SELFTEST.exists():
            raise CannotAnswer("no scripts/selftest.py: there is no suite to measure")
        if not MUTATIONS:
            raise CannotAnswer("the mutation table is empty, so this check asserts nothing. A "
                               "blank table is an undeclared check, which is red by design")
        tmproot = Path(tempfile.mkdtemp(prefix=TMP_PREFIX))
        pristine = _copy(ROOT, tmproot / "pristine", "pristine")
        print("   pristine copy: %s" % pristine, flush=True)
        baseline = None  # LAZY: only a failure needs attributing

        for mut in MUTATIONS:
            print("   family %s: %s" % (mut["family"], mut["why"]), flush=True)
            tree = _copy(pristine, tmproot / ("mutated-" + mut["family"]), "mutated")
            _apply(tree, mut)
            _, failed, names = _run_suite(tree, "mutated(%s)" % mut["family"])
            if not failed:
                print("   %s: PASS. The suite is green with the layer in use." % mut["family"],
                      flush=True)
                continue
            if baseline is None:
                print("   %d failure(s): running the untouched tree to separate a regression from "
                      "a failure that was already there" % failed, flush=True)
                baseline = _run_suite(pristine, "baseline")[2]
            regressions = [n for n in names if n not in baseline]
            preexisting = len(names) - len(regressions)
            if preexisting:
                notes.append("%s: %d failure(s) were already failing on the untouched tree; the "
                             "unit slot owns those" % (mut["family"], preexisting))
            for name in regressions:
                verdict_red.append((mut, name, _locate(name)))
    except CannotAnswer as e:
        print("", flush=True)
        print("FIRST USE: CANNOT ANSWER: %s" % e, flush=True)
        print("This is red, not a stand-down. The check could not measure its property, and a "
              "check that passed on its own inability would be a worse version of the defect it "
              "refuses.", flush=True)
        return 2
    finally:
        if tmproot is not None:
            if keep:
                print("   kept: %s" % tmproot, flush=True)
            else:
                _rmtree(tmproot)

    for n in notes:
        print("   note: %s" % n, flush=True)
    print("   elapsed %.0fs" % (time.monotonic() - t0), flush=True)
    if not verdict_red:
        print("FIRST USE: pass. Every family's sanctioned first use leaves the suite exactly as "
              "green as it was, so no assertion in scripts/suites/ requires this repository's "
              "current emptiness. What that does and does not cover is in this file's docstring.",
              flush=True)
        return 0

    print("", flush=True)
    print("FIRST USE: FAIL. %d assertion(s) passed on the untouched tree and FAIL once the layer "
          "is used as intended. Each one has pinned today's emptiness as a required invariant, so "
          "it reddens for the first person who uses the feature and teaches them that the gate is "
          "noise." % len(verdict_red), flush=True)
    for mut, name, where in verdict_red:
        print("", flush=True)
        print("  %s" % where, flush=True)
        print("  reddened by: %s" % mut["family"], flush=True)
        print("  assertion:   %s" % name[:400], flush=True)
    print("", flush=True)
    print("  THE FIX IS NOT TO DELETE THE ASSERTION. Keep the teeth: require the honest stand-down "
          "when nothing is recorded and the measured branch when something IS recorded, with the "
          "branch chosen by what the assertion just measured. Keep the partition and the "
          "structural invariants unconditional. Only the arm that needs the set to be empty "
          "becomes conditional.", flush=True)
    print("  Reproduce by hand: copy the tree, then in the copy run", flush=True)
    for mut in MUTATIONS:
        for argv_ in mut["writes"]:
            print("    python3 %s %s" % (mut["writer"], " ".join(argv_)), flush=True)
    print("    python3 scripts/selftest.py", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
