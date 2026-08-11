#!/usr/bin/env python3
"""WHAT A RUN OF THE UNIT SUITE IS ALLOWED TO CLAIM (WARP-0717).

This module exists because scripts/selftest.py can now run PART of the suite, and a fast
partial run standing next to a slow gate is a standing invitation to quote the fast one as
if it were verification. The protection is not a banner. It is that the three
verification-bearing acts of a run are three METHODS ON ONE OBJECT, and the object a
partial run gets raises PARTIAL_RUN_CANNOT_VERIFY when asked for any of them.

  1. aggregate_line()        the line `selftest: N passed, M failed` that the gate reads
  2. exit_code()             the process status, which is what verify.sh actually reads
  3. verify_stamp_payload()  the record .veldo/last_verify carries
  4. unit_evidence_check()   the `checks` entry validate.check_required_evidence accepts

WHICH OF THESE HAVE TEETH TODAY, STATED HERE RATHER THAN LEFT TO BE ASSUMED, because two
of them are forward guards and presenting a forward guard as a present one is the failure
this repository has paid for most often:

  aggregate_line and exit_code ARE THE PRESENT-DAY PROTECTION. They have production
  callers on the real path: shared.report() emits through aggregate_line, and
  scripts/selftest.py exits through exit_code. exit_code is the load-bearing one, because
  the stamp is written by scripts/verify.sh IN SHELL, from the exit status of its unit
  slot. A partial run never returns 0, so `if bash -c "$cmd"` cannot succeed on one, so
  the stamp verify.sh writes after a partial unit slot says red. That is how a partial run
  is structurally unable to produce a GREEN stamp, and it is asserted by driving it.

  verify_stamp_payload and unit_evidence_check HAVE NO PRODUCTION CALLER IN THIS
  REPOSITORY TODAY. Nothing in Python writes .veldo/last_verify (verify.sh does, in shell,
  and it is byte-frozen by this item), and proof artifacts are written by hand. These two
  are here so that the FIRST Python-side stamp writer and the FIRST generated unit-evidence
  record have to come through the scope instead of inventing their own authority. They are
  proven non-vacuous in the only way available: the FULL scope's outputs are checked
  against verify.sh's own printf format and against validate.check_required_evidence, so
  the shapes are real, and the PARTIAL scope is refused by name. WHAT THAT DOES NOT DO,
  declared: it cannot stop a human typing a passed unit check into a proof file by hand.
  Nothing in a test suite can. The guard against that is the review, not this module.

THE PREREQUISITE CLOSURE. A fragment cannot run alone: WARP-0712 measured every one of
them PASSES_IN_AGGREGATE_FAILS_ALONE, because the monolith carried cross-region
dependencies through mutated objects and the filesystem and not only through names. So
`--suite NAME` runs NAME plus NAME's measured prerequisite closure, read from the derived
scripts/suites/requires.json. The closure is a FIXPOINT and that is not decoration: taking
each fragment's DIRECT demand only was measured to leave 5 of 13 fragments producing ZERO
of their own labels, because a fragment inside the closure died first.

DERIVED FROM A MEASUREMENT FOR THE FRAGMENTS THE CUT COVERED, AND HAND-TYPED FOR EVERY
FRAGMENT ADDED SINCE. Stating it the other way round would be the more flattering half of
the truth and it is the half that governs every future fragment. For a fragment with a
region range, the demand comes from proof/WARP-0712/order-dependence.json and nobody types
it. For a fragment added after that cut there is no range, so direct_demand takes the
`requires` list a HUMAN TYPED in manifest.json at face value and only closes it
transitively. WHAT FAIL-CLOSED BUYS THERE AND WHAT IT DOES NOT: a MISSING declaration is a
refusal (ClosureUnavailable), and a WRONG one is not detectable here at all. Measured: a
fragment declaring `requires: [itself]` while using a name another fragment binds is
ACCEPTED, its freshness check passes, and `--suite <it>` then dies on a NameError with no
verdict line, which is worse than a red. The only instrument that finds a wrong declaration
is running the closure and comparing the fragment's own labels against its full-run labels,
which is what proof/WARP-0717/inner-loop-measurement.json does per fragment.

  python3 scripts/run_scope.py --emit-requires    regenerate scripts/suites/requires.json
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUITES = ROOT / "scripts" / "suites"
MANIFEST_PATH = SUITES / "manifest.json"
REQUIRES_PATH = SUITES / "requires.json"
MEASUREMENT_PATH = ROOT / "proof" / "WARP-0712" / "order-dependence.json"

# The one refusal name this item adds. It is a refusal and not a warning because this
# item's whole risk is gradual erosion, and a warning is a thing people learn to ignore.
REFUSAL = "PARTIAL_RUN_CANNOT_VERIFY"

# A partial run's exit status. Never 0, so no exit-status consumer can read it as a pass,
# and distinct from 1 so a partial run that PASSED stays distinguishable from one that
# FAILED. This is the same pair --upto has used since WARP-0712.
PARTIAL_PASSED_EXIT = 2
PARTIAL_FAILED_EXIT = 1


class PartialRunCannotVerify(Exception):
    """Raised when a partial run is asked for one of the acts only a full run may perform.

    The message LEADS with the refusal name, because the name is what gets asserted and
    what gets grepped out of a captured log.
    """

    def __init__(self, act, selector=None):
        self.act = act
        self.selector = selector
        msg = "%s: a partial run was asked to %s" % (REFUSAL, act)
        if selector:
            msg += " (selector: %s)" % selector
        super().__init__(msg)


class UnknownSuite(Exception):
    """Raised when a selector names something the manifest does not enumerate.

    A selector that matches nothing and exits 0 would report success for having tested
    nothing, which is the most dangerous output this feature could have. So an unresolvable
    name is a refusal that NAMES what is available, and there is no prefix matching, no
    glob expansion and no empty-selector-means-everything.
    """

    def __init__(self, bad, available):
        self.bad = bad
        self.available = list(available)
        super().__init__(
            "UNKNOWN_SUITE: %r is not a suite this manifest enumerates.\n"
            "  available (%d):\n%s"
            % (bad, len(available), "".join("    %s\n" % n for n in available)))


class ClosureUnavailable(Exception):
    """Raised when a suite has no prerequisite closure on record.

    Fail closed. A fragment added after the WARP-0712 measurement has no region range in
    it, so its closure cannot be derived; it must DECLARE one in the manifest. A fragment
    with neither a measured range nor a declaration gets a refusal, never an empty closure,
    because an empty closure would silently run it alone and it would die on a NameError
    that looks like a defect in the fragment.
    """

    def __init__(self, name, why):
        super().__init__("CLOSURE_UNAVAILABLE: %s: %s" % (name, why))


def load_manifest(path=None):
    return json.loads(Path(path or MANIFEST_PATH).read_text())


def fragments(manifest):
    """The manifest's fragments in order: everything it enumerates except the shared
    preamble, which is not selectable because it is not optional."""
    return [s for s in manifest["suites"] if s["file"] != manifest["shared"]]


def _region_range(entry):
    m = re.match(r"^(\d+)\s*-\s*(\d+)$", str(entry.get("regions", "")).strip())
    return (int(m.group(1)), int(m.group(2))) if m else None


def direct_demand(manifest, measurement):
    """THE DIRECT DEMAND of every fragment, as a name list in manifest order.

    For a fragment the WARP-0712 measurement covers: the fragments owning the regions this
    fragment's own regions were MEASURED to need (measurement["closures"], produced by
    scripts/suite_slice.py), plus itself.

    For a fragment added AFTER that cut, which therefore has no region range in it: the
    `requires` list the manifest DECLARES, plus itself. A fragment with neither is a
    refusal, never an empty set.

    THIS IS NOT A PREREQUISITE SET ON ITS OWN. It is not closed under itself, and running
    it was MEASURED to leave 5 of 13 fragments producing zero of their own labels. Callers
    want transitive_close() over this. It is exposed separately so the suite can prove the
    closing step changes the answer instead of restating it.
    """
    frag = fragments(manifest)
    names = [s["name"] for s in frag]
    pos = {n: i for i, n in enumerate(names)}

    r2f, measured = {}, {}
    for i, s in enumerate(frag):
        rng = _region_range(s)
        if rng:
            measured[i] = rng
            for r in range(rng[0], rng[1] + 1):
                r2f[r] = i

    by_region = {c["region"]: c for c in measurement["closures"]}
    out = {}
    for i, s in enumerate(frag):
        if i in measured:
            a, b = measured[i]
            dep = set()
            for r in range(a, b + 1):
                if r in by_region:
                    dep |= set(by_region[r]["closure"])
            need = {r2f[x] for x in dep if x in r2f} | {i}
        else:
            declared = s.get("requires")
            if not isinstance(declared, list) or not declared:
                raise ClosureUnavailable(
                    s["name"],
                    "no parsable region range in the WARP-0712 measurement and no declared "
                    "`requires` in the manifest, so its prerequisites are unknown")
            unknown = [n for n in declared if n not in pos]
            if unknown:
                raise ClosureUnavailable(
                    s["name"], "declares requires on names the manifest does not "
                               "enumerate: %s" % sorted(unknown))
            need = {pos[n] for n in declared} | {i}
        out[names[i]] = [names[j] for j in sorted(need)]
    return out


def transitive_close(demand):
    """The FIXPOINT of a demand relation: each key mapped to the closure of its members.

    Order is preserved from the input's own key order, which is manifest order.
    """
    keys = list(demand)
    pos = {n: i for i, n in enumerate(keys)}
    closure = {n: set(v) for n, v in demand.items()}
    changed = True
    while changed:
        changed = False
        for n in keys:
            grown = set(closure[n])
            for m in list(closure[n]):
                grown |= set(demand[m])
            if grown != closure[n]:
                closure[n] = grown
                changed = True
    return {n: sorted(closure[n], key=lambda x: pos[x]) for n in keys}


def derive_requires(manifest, measurement):
    """The prerequisite CLOSURE of every fragment: the fixpoint of the direct demand."""
    return transitive_close(direct_demand(manifest, measurement))


def requires_document(manifest=None, measurement=None):
    """The derived requires.json content, as a dict."""
    manifest = manifest or load_manifest()
    if measurement is None:
        measurement = json.loads(MEASUREMENT_PATH.read_text())
    table = derive_requires(manifest, measurement)
    return {
        "schema": "veldo.suite_requires/v1",
        "note": "DERIVED, do not edit by hand. Regenerate with "
                "`python3 scripts/run_scope.py --emit-requires`; "
                "scripts/check_generated.sh holds it fresh. Each entry is the fragment's "
                "prerequisite CLOSURE, in manifest order, INCLUDING the fragment itself. "
                "`python3 scripts/selftest.py --suite NAME` runs exactly this list. It is a "
                "FIXPOINT: the direct demand alone was measured to leave 5 of 13 fragments "
                "producing zero of their own labels, because a fragment inside the closure "
                "died first. WHERE EACH ENTRY COMES FROM, because the two halves are not "
                "equally trustworthy: a fragment WITH a region range takes its demand from "
                "the WARP-0712 measurement and nobody types it, while a fragment added "
                "after that cut has no range and its demand is the `requires` list a HUMAN "
                "TYPED in manifest.json, closed transitively. A MISSING declaration is a "
                "refusal by name. A WRONG one is accepted here and only surfaces as a "
                "NameError under `--suite`, with no verdict line, so a post-cut fragment's "
                "declaration is worth exactly the label-identity check behind it.",
        "derived_from": {
            "measurement": "proof/WARP-0712/order-dependence.json",
            "digest": measurement.get("digest", ""),
            "manifest": "scripts/suites/manifest.json",
        },
        "requires": table,
    }


def load_requires(path=None):
    return json.loads(Path(path or REQUIRES_PATH).read_text())["requires"]


def resolve(selector_values, manifest=None, requires=None):
    """(selected_names, closure_names) for a list of --suite values.

    Each value may name one suite or several separated by commas, so `--suite a,b` and
    `--suite a --suite b` mean the same thing. The result is the UNION of the named
    suites' closures, in manifest order. Every name must resolve exactly: no prefix
    matching, no glob expansion, and the empty string is a name like any other and
    resolves to nothing, so it refuses.
    """
    manifest = manifest or load_manifest()
    frag = fragments(manifest)
    names = [s["name"] for s in frag]
    if requires is None:
        requires = load_requires()

    asked = []
    for value in selector_values:
        # A value is split on commas and NOT stripped of anything else: a name with a
        # glob character in it is looked up literally, which is why `*` refuses instead of
        # matching everything. An empty value yields one empty name, which also refuses.
        parts = value.split(",") if "," in value else [value]
        asked.extend(parts)
    if not asked:
        raise UnknownSuite("", names)

    for name in asked:
        if name not in names:
            raise UnknownSuite(name, names)

    wanted = set()
    for name in asked:
        closure = requires.get(name)
        if not closure:
            raise ClosureUnavailable(
                name, "scripts/suites/requires.json carries no closure for it; regenerate "
                      "with `python3 scripts/run_scope.py --emit-requires`")
        for dep in closure:
            if dep not in names:
                raise ClosureUnavailable(
                    name, "its closure names %r, which the manifest does not enumerate" % dep)
            wanted.add(dep)

    return asked, [n for n in names if n in wanted]


class RunScope:
    """The one authority on what a single run of the unit suite may claim.

    Constructed exactly once, by scripts/selftest.py, from the parsed command line. There
    is no second constructor on the real path, which is what makes "a partial run cannot
    do X" a property of the run rather than a property of a particular call site.
    """

    def __init__(self, selector, running, declared):
        # selector is None for the full manifest and a human-readable string otherwise.
        # It is the ONLY thing that decides partiality: not the count of suites, because a
        # selector that happened to name every suite still ran under a selector and still
        # must not be able to claim verification.
        self.selector = selector
        self.running = list(running)
        self.declared = list(declared)

    @property
    def partial(self):
        return self.selector is not None

    def _refuse(self, act):
        if self.partial:
            raise PartialRunCannotVerify(act, self.selector)

    # ---- the four verification-bearing acts -------------------------------------------

    def aggregate_line(self, passed, failed):
        """The aggregate summary line the gate and the operator guide parse."""
        self._refuse("emit the aggregate summary line")
        return "selftest: %d passed, %d failed" % (passed, failed)

    def exit_code(self, failed):
        """The process exit status. 0 means verified and a partial run never returns it."""
        if self.partial:
            return PARTIAL_FAILED_EXIT if failed else PARTIAL_PASSED_EXIT
        return 1 if failed else 0

    def verify_stamp_payload(self, commit, status, at, checks_run, checks_na):
        """The record .veldo/last_verify carries. See the module docstring: verify.sh writes
        that file in shell and this has no production caller yet, deliberately."""
        self._refuse("write the verify stamp (.veldo/last_verify)")
        return {"commit": commit, "status": status, "at": at,
                "checks_run": checks_run, "checks_na": checks_na}

    def unit_evidence_check(self, failed):
        """The `checks` entry a proof artifact carries for the unit slot, which is what
        validate.check_required_evidence reads. No production caller yet; see the module
        docstring for what that does and does not buy."""
        self._refuse("satisfy the required-evidence check")
        return {"name": "unit", "status": "failed" if failed else "passed"}

    # ---- the partial run's own, clearly different, output -----------------------------

    def partial_line(self, passed, failed, elapsed_s):
        """A partial run's final line. It is NOT the aggregate line, and the existing
        --upto text is a strict PREFIX of it so anything that already recognised a partial
        run still does."""
        return ("selftest (PARTIAL, %d of %d suites): %d passed, %d failed in %.2fs"
                % (len(self.running), len(self.declared), passed, failed, elapsed_s))

    def banner(self):
        """The banner a partial run prints BEFORE it runs anything.

        It has to be impossible to lose in a scrollback: someone pasting output must be
        able to tell a partial run from a gate run without being told which command
        produced it. So it names itself, names what ran, names what did not, and names the
        four things it is structurally unable to produce.
        """
        if not self.partial:
            return ""
        skipped = [n for n in self.declared if n not in self.running]
        rule = "=" * 78
        lines = [
            rule,
            "PARTIAL RUN OF THE UNIT SUITE. THIS IS NOT VERIFICATION AND CANNOT BECOME IT.",
            rule,
            "  selector    %s" % self.selector,
            "  running     %d of %d suites: %s" % (len(self.running), len(self.declared),
                                                   ", ".join(self.running)),
            "  skipped     %d: %s" % (len(skipped), ", ".join(skipped) if skipped else "none"),
            "  why these   the named suites plus their measured prerequisite closure",
            "              (scripts/suites/requires.json). No fragment runs alone: every",
            "              one of them was measured PASSES_IN_AGGREGATE_FAILS_ALONE.",
            "  cannot      emit the aggregate summary line, write .veldo/last_verify, or",
            "              produce a passed unit-evidence record. Each raises %s." % REFUSAL,
            "  exit        never 0, even when nothing fails.",
            "  done means  `bash scripts/verify.sh` green, and nothing else.",
            rule,
        ]
        return "\n".join(lines)

    def footer(self):
        """The last thing a partial run prints, after its own count."""
        if not self.partial:
            return ""
        return ("PARTIAL RUN: no proof manifest, no evidence claim and no landing decision "
                "may cite this. Only a green `bash scripts/verify.sh` means done.")


def full_scope(manifest=None):
    """The scope of a run with NO selector: the whole manifest, allowed to claim."""
    manifest = manifest or load_manifest()
    names = [s["name"] for s in fragments(manifest)]
    return RunScope(None, names, names)


def main(argv):
    if argv[1:] == ["--emit-requires"]:
        doc = requires_document()
        REQUIRES_PATH.write_text(json.dumps(doc, indent=1) + "\n")
        print("run_scope: wrote %s (%d suites)"
              % (REQUIRES_PATH.relative_to(ROOT), len(doc["requires"])))
        return 0
    print(__doc__.strip().splitlines()[0])
    print("usage: run_scope.py --emit-requires")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
