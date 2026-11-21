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
import os
import re
import selectors
import signal
import subprocess
import sys
import tempfile
import time
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


# THE GATE'S LEGS (VELDO-0208, owner decision 2026-10-07). The authority's scripts/gate_legs.py
# runs a declared stage twice and tells the run which leg it is through these three variables:
# VELDO_GATE_LEG is "confined" or "unconfined", VELDO_GATE_UNCONFINED is the authority's list,
# comma-separated, each entry a suite name or name:rows for a suite only some rows of which run
# unconfined, and VELDO_GATE_DECLARATION is the sha256 digest of the list gate_legs.py read. All
# three unset, the run is the whole suite exactly as before. A leg is not a selector: the gate runs
# both legs and requires both, and a person running one leg by hand has run half the stage.
# A leg run that is not what gate_legs.py sets, three variables naming a leg, a digest and a
# non-empty well-formed list, is REFUSED rather than read: an empty list once made an unconfined leg
# run zero suites and print a passing aggregate line.
GATE_LEG = "VELDO_GATE_LEG"
GATE_UNCONFINED = "VELDO_GATE_UNCONFINED"
GATE_DECLARATION = "VELDO_GATE_DECLARATION"
GATE_VARIABLES = (GATE_LEG, GATE_UNCONFINED, GATE_DECLARATION)
LEGS = ("confined", "unconfined")


class LegRefused(Exception):
    """Leg variables that are not the complete, well-formed set the authority's leg runner sets."""


def gate_leg(environ):
    """(leg or None, {suite: rows tag or None for the whole suite}) from the environment."""
    present = [name for name in GATE_VARIABLES if environ.get(name) is not None]
    if not present:
        return None, {}
    if len(present) != len(GATE_VARIABLES):
        raise LegRefused("leg variables %s are set without %s; only the authority's gate_legs.py "
                         "starts a leg, and it sets all three"
                         % (", ".join(present), ", ".join(n for n in GATE_VARIABLES if n not in present)))
    leg = environ[GATE_LEG]
    if leg not in LEGS:
        raise LegRefused("%s=%r names no leg (%s)" % (GATE_LEG, leg, ", ".join(LEGS)))
    if not re.match(r"^sha256:[0-9a-f]{64}$", environ[GATE_DECLARATION]):
        raise LegRefused("%s=%r is not the digest of a declared list"
                         % (GATE_DECLARATION, environ[GATE_DECLARATION]))
    if not environ[GATE_UNCONFINED]:
        raise LegRefused("%s is empty; a leg without the authority's list is not a leg" % GATE_UNCONFINED)
    listed = {}
    for item in environ[GATE_UNCONFINED].split(","):
        name, _, rows = item.partition(":")
        if not re.match(r"^[0-9A-Za-z][0-9A-Za-z_]*$", name) or (rows and not re.match(r"^[a-z][a-z0-9-]*$", rows)) \
                or (":" in item and not rows) or name in listed:
            raise LegRefused("%s carries a malformed or repeated entry %r" % (GATE_UNCONFINED, item))
        listed[name] = rows or None
    return leg, listed


def leg_runs(suite, rows=None, environ=None):
    """Whether this leg runs the given rows of `suite`: rows=None is the suite's ordinary rows, a
    tag names the rows the list may move to the unconfined leg. Outside a leg everything runs."""
    leg, listed = gate_leg(environ if environ is not None else __import__("os").environ)
    if leg is None:
        return True
    scoped = suite in listed
    if leg == "confined":
        return not (scoped and listed[suite] is not None and listed[suite] == rows)
    if not scoped:
        return False
    return listed[suite] is None or listed[suite] == rows


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

    def verify_stamp_payload(self, commit, status, at, checks_run, checks_na,
                             veldo_version=None, tree=None, force_fresh=False, reused=None,
                             reuse_evidence=None, unconfined=None):
        """The record .veldo/last_verify carries. See the module docstring: verify.sh writes
        that file in shell and this has no production caller yet, deliberately.

        veldo_version is the version that PRODUCED the run (VELDO-0010), and None is a real
        value rather than a missing one: the gate writes null when the version cannot be read,
        because a gate record is exactly where an invented version would be believed. The key
        set here is asserted EQUAL to verify.sh's own printf keys, which is how this stayed in
        step - adding the field to the gate reddened that assertion until it was added here.

        tree is WHAT THE RUN ACTUALLY VERIFIED (VELDO-0010's sibling, ledger finding 69), and it is
        the second field to prove that coupling by breaking it: adding `tree` to the gate's printf
        reddened the key-set assertion here until this signature carried it too, exactly as
        veldo_version did. "clean", a count of dirty paths, or None when git could not answer -
        and None is a real value rather than a missing one, because an unanswered question and a
        clean tree invite opposite conclusions. The record used to name only the commit, which
        after a gate-then-commit is systematically a state it had not verified.

        force_fresh and reused are the freshness fields scripts/reuse_stamp.py hands the gate
        (VELDO-0208: "Both reused and force_fresh are mandatory on stamps and events"). reused is
        {"unit": 0, "mutation": <count>}, or the gate's fallback with mutation None when no valid
        receipt existed. reuse_evidence is present only when a reused result had to be
        authenticated, exactly as reuse_stamp.fields adds it only then.

        unconfined is what scripts/gate_legs.py --stamp returns (VELDO-0208, owner decision
        2026-10-07): the declaration's digest and the entries each stage ran outside the
        confinement, or None when a leg was expected and its record could not be read (the gate is
        then RED). Like reuse_evidence it is present only when an unconfined leg was expected."""
        self._refuse("write the verify stamp (.veldo/last_verify)")
        payload = {"commit": commit, "status": status, "at": at,
                   "checks_run": checks_run, "checks_na": checks_na,
                   "veldo_version": veldo_version, "tree": tree, "force_fresh": force_fresh,
                   "reused": reused if reused is not None else {"mutation": None, "unit": 0}}
        if reuse_evidence is not None:
            payload["reuse_evidence"] = reuse_evidence
        if unconfined is not None:
            payload["unconfined"] = unconfined
        return payload

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


# =============================================================================================
# VELDO-0221: A GATE LEG RUNS ITS SUITES AS ISOLATED PARALLEL CLOSURE SHARDS
# =============================================================================================
#
# In a gate leg scripts/selftest.py no longer executes the leg's suites one after another in one
# interpreter. It hands them to run_shards below: one SHARD per suite of the leg, a fresh
# interpreter (`selftest.py --suite NAME --shard FD --shard-root DIR`) that executes the suite's
# prerequisite closure from scripts/suites/requires.json in manifest order in one namespace and
# then the suite. A bare run and a selector keep the ordered single-namespace run.
#
# ISOLATED BY CONSTRUCTION (owner decision D1), not inferred from a clean run:
#   - separate interpreters share no Python state;
#   - every shard has its own HOME, TMPDIR, XDG configuration, data, cache and state directories
#     and its own runtime directory in place of /run/user/<uid>, which holds only links to the
#     user manager's own sockets (its bus and systemd/private), so units still reach the one
#     manager and nothing else of the real runtime directory is in the shard's reach by name;
#   - a shard reports over a pipe it inherits, never through a shared file;
#   - in a confined leg each shard stacks its own Landlock layer on the leg's domain
#     (scripts/agent_sandbox.py write_layer), which grants writes only beneath its own roots, and proves it
#     by a write the dispatcher planted a target for and the kernel must refuse;
#   - the engine names what it creates on the one user manager with the instance name the
#     dispatcher writes into each shard's configuration directory (INSTANCE_FILE): the suite's.
#
# CHECKED IN EVERY GATE, force-fresh or not. A confined shard must report its layer in force
# before its suite runs and must leave its probe unwritten. An unconfined leg, which cannot be
# confined, is read before, at every shard's end and after, in the shared places a suite can
# reach (unconfined_places and the user manager's units). What appeared and stayed is
# isolation_breach, RED, naming the suite.
#
# WHAT THE CHECK CAN AND CANNOT ATTRIBUTE, measured on the qualification host on 2026-11-21 and
# stated because a check that turned every gate red would be ignored. The host is shared: in 260
# seconds other sessions made 20 entries at the top of /tmp, two units and one /dev/shm entry,
# and this gate's own launchers and mutation workers make more. The kernel records no creator
# for a file, so a NEW ITEM IS THE LEG'S when one of these holds: its name carries a suite's
# instance name; it refers to a shard's roots (a link's target, a small file's text, a unit's
# properties); or a live process that carries a shard's roots in its environment holds it. An
# item a live process of another tree holds, or that another account owns, is foreign. For
# what is left, each place has a rule: `strict` places are waited on until the item is gone
# (SETTLE_S, a hang detector) and what stays is a breach charged to the suites that ran when it
# first appeared; the top of the system temporary directory is `attributed`, because this gate
# itself makes entries there throughout the leg, so an unattributed entry there is printed by
# name and not charged.

SHARD_DEADLINE_S = 1800.0   # one shard; a hang detector, never a pace
SHARD_TICK_S = 2.0          # how often a waiting dispatcher samples memory and asks the ledger again
SETTLE_S = 300.0            # how long a foreign-looking item in a strict place may take to go
SHARD_UNMEASURED = {"cpu": 1.0, "memory": 1 << 30}
# The leg's own channel to the authority's leg runner, which asks the gate ledger for each shard
# (scripts/gate_legs.py ShardClaims). The gate ledger's own channel never reaches this dispatcher.
LEDGER_CHANNEL = "VELDO_GATE_SHARD_LEDGER_FD"
SHARD_CLAIMS = "VELDO_GATE_SHARD_CLAIMS"
SHARD_METRICS = "VELDO_GATE_SHARD_METRICS_FD"
FORCE_FRESH = "VELDO_GATE_FORCE_FRESH"
INSTANCE_FILE = ("veldo", "instance.json")
INSTANCE_SCHEMA = "veldo.instance/v1"
FAIL_MARK = "SELFTEST FAIL:"
UNCOUNTED_MARK = "SELFTEST ROW-FAIL (not counted in this shard):"
ISOLATION_BREACH = "isolation_breach"
# Every way a shard fails its suite without a failed row of the suite's own. Each is one counted
# failure with one FAIL line whose text is fixed, so two runs of one tree name it identically.
SHARD_FAILURES = ("closure_unavailable", "no_verdict", "asserted_nothing", "deadline_exceeded",
                  "prerequisite_failed", "exit_status", ISOLATION_BREACH)
# A shard's roots are sibling directories in one directory of the leg's own, named by the shard's
# two-character tag: the temporary directory is the tag alone and every other root the tag and one
# letter. A SHARD'S TEMPORARY DIRECTORY MUST NOT BE LONGER THAN THE LEG'S, because a suite binds
# local sockets beneath it and a socket path holds under 108 bytes. Measured in the confined leg:
# with 18 bytes added one suite's path was 3 over, and with 13 added two more suites' were. So in
# the gate's confined leg, whose temporary directory is `tmp` in the launcher's scratch, a shard's
# temporary directory is a three-character sibling of it (short_temporary), exactly as long. The
# launcher removes its scratch, and those directories with it, when the leg's command ends.
SHARD_ROOTS = (("TMPDIR", ""), ("HOME", "h"), ("XDG_CONFIG_HOME", "c"), ("XDG_DATA_HOME", "d"),
               ("XDG_CACHE_HOME", "k"), ("XDG_STATE_HOME", "s"), ("XDG_RUNTIME_DIR", "r"))
SHARD_PROBES = "p"
# THE SHARDS THAT RUN WITHOUT A LANDLOCK LAYER OF THEIR OWN, each with its reason. This table is the
# only way out of the layer, it lives in this protected file, every leg prints what it exempted, and
# an entry is a reviewed decision, never a convenience. A shard named here still has its own roots,
# its own result pipe and the broker's hold on its binds, and still runs inside the leg's domain;
# what it loses is the kernel's refusal of a write to another shard's roots.
UNLAYERED = {
    "151_veldo_0313_space_run":
        "its rows judge what every process of the leg's tree holds: the space probe reads each "
        "process's working directory and open files, and a process in a Landlock domain of its own "
        "is refused the dispatcher's and every other shard's, so each of them counts as an unread "
        "process that may hold the run's folders and the run never ends. In the leg's own domain "
        "it reads them, as it did in the ordered run",
}

# The two arguments a shard interpreter is started with. The gate launcher's broker knows a shard by
# them (scripts/agent_sandbox.py Broker._shard_roots) and holds its binds to its roots.
SHARD_ARGUMENTS = ("--shard", "--shard-root")
MANAGER_SOCKETS = ("bus", "systemd/private")
# What a shard does not inherit: the dispatcher's own channels and inputs, a diagnostic order, and
# the other spellings of the temporary directory, which would outrank the shard's own TMPDIR.
SHARD_DROPPED = (LEDGER_CHANNEL, SHARD_CLAIMS, SHARD_METRICS, "VELDO_SUITE_ORDER", "TMP", "TEMP",
                 "TEMPDIR")


def leg_suites(leg, listed, names):
    """The suites of one gate leg, in the given order: the confined leg runs every suite the
    authority's list does not name whole, the unconfined leg only the listed ones. A suite listed
    for some rows is in both, and its rows ask leg_runs which leg owns them. Each suite of a leg is
    one shard's target exactly once, by construction from this list."""
    whole = {name for name, rows in listed.items() if rows is None}
    if leg == "confined":
        return [name for name in names if name not in whole]
    return [name for name in names if name in listed]


class ShardResources:
    """The manifest's declared resources, admitted by the dispatcher: a positive count shares a
    resource's slots and `exclusive` takes them all, so a suite that declares the systemd user
    manager exclusive runs beside no other user of it. A waiting suite bars every later user of
    the resources it waits for, so an exclusive one cannot starve."""

    def __init__(self, manifest):
        self.capacity = dict(manifest.get("resource_capacities") or {})
        self.demands = {}
        for suite in fragments(manifest):
            demand = suite.get("resources") or {}
            resolved = {}
            for resource, slots in demand.items():
                capacity = self.capacity.get(resource)
                if slots == "exclusive":
                    slots = capacity
                if type(capacity) is not int or type(slots) is not int or not 0 < slots <= capacity:
                    raise LegRefused("suite %s declares an impossible demand on %r"
                                     % (suite["name"], resource))
                resolved[resource] = slots
            self.demands[suite["name"]] = resolved
        self.used = dict.fromkeys(self.capacity, 0)
        self.held = {}

    def demand(self, name):
        return self.demands.get(name, {})

    def exclusive(self, name):
        return sorted(r for r, n in self.demand(name).items() if n == self.capacity[r])

    def fits(self, name):
        return all(self.used[r] + n <= self.capacity[r] for r, n in self.demand(name).items())

    def acquire(self, name):
        self.held[name] = self.demand(name)
        for resource, slots in self.held[name].items():
            self.used[resource] += slots

    def release(self, name):
        for resource, slots in self.held.pop(name, {}).items():
            self.used[resource] -= slots


class ShardLedger:
    """The gate-wide ledger (VELDO-0216) as the authority's leg runner serves it to this dispatcher:
    one request and one reply per line. The runner forwards each request with its own measured
    claim for the suite. A refusal means ask again later, never start."""

    def __init__(self, descriptor):
        import socket
        self.socket = socket.socket(fileno=os.dup(int(descriptor)))
        self.file = self.socket.makefile("rwb", buffering=0)
        self.peak = 0

    def request(self, operation, name, claim=None):
        self.file.write((json.dumps({"operation": operation, "name": name, "claim": claim}) + "\n").encode())
        raw = self.file.readline(65537)
        if not raw or len(raw) > 65536:
            raise LegRefused("the gate ledger closed its channel or sent an oversized reply")
        answer = json.loads(raw)
        if "error" in answer:
            raise LegRefused("the gate ledger refused the %s of %s: %s" % (operation, name, answer["error"]))
        return answer

    def acquire(self, name, claim):
        return bool(self.request("acquire", name, {"cpu": claim["cpu"], "memory": claim["memory"],
                                                    "manager": "none", "ports": [],
                                                    "host_lock": "none"})["granted"])

    def release(self, name):
        self.request("release", name)

    def close(self):
        self.file.close()
        self.socket.close()


def usable_cpus(cgroup_root="/sys/fs/cgroup", membership="/proc/self/cgroup"):
    """The cores this process may use: its affinity, bounded by every cgroup quota above it."""
    cpus = float(len(os.sched_getaffinity(0)))
    try:
        own = Path(membership).read_text().split("::", 1)[1].strip()
        path = Path(cgroup_root) / own.lstrip("/")
        for directory in [path, *path.parents]:
            if directory != Path(cgroup_root) and Path(cgroup_root) not in directory.parents:
                break
            limit = directory / "cpu.max"
            if limit.exists():
                quota, period = limit.read_text().split()
                if quota != "max":
                    cpus = min(cpus, int(quota) / int(period))
    except (OSError, ValueError, IndexError):
        pass
    return max(1, int(cpus))


def handed_claims(environ):
    """{suite: {cpu, memory, seconds}} the authority's leg runner measured in earlier gates and
    handed this leg, or {}. An entry that is not finite positive numbers is dropped by name."""
    try:
        document = json.loads(environ.get(SHARD_CLAIMS) or "{}")
    except ValueError:
        return {}
    claims = {}
    for name, item in (document.items() if isinstance(document, dict) else ()):
        try:
            cpu, memory = float(item["cpu"]), float(item["memory"])
            seconds = float(item.get("seconds", 0))
        except (TypeError, KeyError, ValueError, AttributeError):
            continue
        if 0 < cpu < float("inf") and 0 < memory < float("inf") and 0 <= seconds < float("inf"):
            claims[name] = {"cpu": cpu, "memory": memory, "seconds": seconds}
    return claims


def shard_tag(index):
    """A shard's tag: two characters for the first 1296 shards of a leg, its number after that."""
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    return digits[index // 36] + digits[index % 36] if index < 1296 else "%d" % index


def roots_of(root):
    """Every private root of the shard whose temporary directory is `root`."""
    return {variable: Path(str(root) + leaf) for variable, leaf in SHARD_ROOTS}


def shard_roots(base, index):
    """(a shard's own path prefix, {environment variable: its private root})."""
    root = Path(base) / shard_tag(index)
    return root, roots_of(root)


def leg_scratch(environ, root):
    """The gate launcher's scratch this leg runs in, or None: its HOME, named with the launcher's
    own prefix, holding the leg's temporary directory `tmp`. Only there is a sibling of the leg's
    temporary directory a private place of this leg's."""
    home, temporary = environ.get("HOME"), environ.get("TMPDIR")
    launcher = shard_launcher(root)
    if not home or not temporary or not launcher.is_file():
        return None
    prefix = re.search(r"^SCRATCH_PREFIX = '([A-Za-z0-9._-]+)'$", launcher.read_text(), re.M)
    if prefix and Path(home).name.startswith(prefix.group(1)) and Path(temporary) == Path(home) / "tmp":
        return Path(home)
    return None


def short_temporary(scratch):
    """A new three-character directory in the launcher's scratch for one shard's temporary files,
    as long as the leg's own `tmp`, or None when none could be made."""
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    for _attempt in range(64):
        number = int.from_bytes(os.urandom(2), "big") % 1296
        path = Path(scratch) / ("t" + digits[number // 36] + digits[number % 36])
        try:
            os.mkdir(path, 0o700)
            return path
        except FileExistsError:
            continue
        except OSError:
            return None
    return None


def link_manager(runtime, real):
    """Make the shard's runtime directory hold links to the user manager's own sockets and nothing
    else; the names it could link. A manager that is not there, or not in reach, links nothing."""
    linked = []
    for relative in MANAGER_SOCKETS:
        source = Path(real) / relative
        try:
            if not source.is_socket():
                continue
            target = Path(runtime) / relative
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.symlink(source, target)
            linked.append(relative)
        except OSError:
            continue
    return linked


def shard_environment(environ, roots, linked, base):
    """What one shard runs with: the leg's environment (its leg variables included), its own roots
    in place of the leg's, and none of the dispatcher's channels."""
    env = {k: v for k, v in environ.items() if k not in SHARD_DROPPED}
    env.update({variable: str(path) for variable, path in roots.items()})
    # A shard's temporary directory is its own, never the leg's, which every shard would share.
    env["TMPDIR"] = str(roots["TMPDIR"])
    env.pop("DBUS_SESSION_BUS_ADDRESS", None)
    if "bus" in linked:
        env["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=%s/bus" % roots["XDG_RUNTIME_DIR"]
    return env


def write_instance(config, name):
    """The installation's configuration of this shard: the engine reads its instance name here and
    names every unit, slice, service and runtime directory it creates with it."""
    path = Path(config).joinpath(*INSTANCE_FILE)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema": INSTANCE_SCHEMA, "prefix": name}) + "\n")
    return path


def launcher_fds(root):
    """Inside a tree the agent launcher made, the tree's marker, which a suite's nested gate needs
    (VELDO-0210 AC6); nothing elsewhere or in a tree with no launcher."""
    path = Path(root) / "scripts" / "agent_sandbox.py"
    if not path.is_file():
        return ()
    import importlib.util
    spec = importlib.util.spec_from_file_location("veldo_shard_launcher", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return tuple(module.launcher_fds())


# ---- the shard's own side ----------------------------------------------------------------------

class ShardReport:
    """The shard's end of its result channel: one JSON record per line on the pipe it inherited."""

    def __init__(self, descriptor):
        self.descriptor = int(descriptor)
        os.set_inheritable(self.descriptor, False)  # no process the suite starts can write a verdict

    def send(self, **record):
        data = (json.dumps(record) + "\n").encode()
        while data:
            data = data[os.write(self.descriptor, data):]


def die_with_dispatcher():
    """A shard never outlives its dispatcher: the kernel kills it when the dispatcher ends."""
    import ctypes
    ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGKILL, 0, 0, 0)


def shard_probe(root):
    """The file the dispatcher expects a confined shard to be REFUSED: beside the shards' roots,
    inside what the leg's own domain may write, outside what this shard's layer grants."""
    root = Path(root)
    return root.parent / SHARD_PROBES / root.name


def shard_launcher(root):
    """The launcher module a confined shard takes its Landlock layer from: the tree's own
    scripts/agent_sandbox.py, the one module a Landlock or seccomp rule may live in (VELDO-0208)."""
    return Path(root) / "scripts" / "agent_sandbox.py"


def confine_shard(root, launcher, environ=None):
    """Stack this shard's Landlock layer and prove it: (in force, the probe write was refused,
    what went wrong). Called before any suite code runs, so the roots are the ones the dispatcher
    put in this shard's environment."""
    import importlib.util
    environ = os.environ if environ is None else environ
    try:
        spec = importlib.util.spec_from_file_location("veldo_shard_sandbox", launcher)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.write_layer([Path(environ[variable]) for variable, _leaf in SHARD_ROOTS])
    except Exception as error:  # noqa: BLE001 - any failure is reported, and the dispatcher reddens
        return False, False, "%s: %s" % (type(error).__name__, error)
    try:
        os.close(os.open(shard_probe(root), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
    except PermissionError:
        return True, True, ""
    except OSError as error:
        return True, False, "the probe write ended %s, not a refusal" % error
    return True, False, "the probe write outside the shard's roots succeeded"


# ---- the shared places an unconfined leg can reach ----------------------------------------------

def manager_units():
    """The user manager's loaded units and slices by name, or None when it does not answer."""
    env = dict(os.environ, XDG_RUNTIME_DIR="/run/user/%d" % os.getuid())
    env.pop("DBUS_SESSION_BUS_ADDRESS", None)
    try:
        proc = subprocess.run(["systemctl", "--user", "list-units", "--all", "--no-legend", "--plain",
                               "--full"], capture_output=True, text=True, timeout=120, env=env,
                              stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode:
        return None
    return [line.split()[0] for line in proc.stdout.splitlines() if line.split()]


def describe_unit(unit):
    """What a unit runs and where, as the manager shows it: the text a shard's roots are sought in."""
    env = dict(os.environ, XDG_RUNTIME_DIR="/run/user/%d" % os.getuid())
    env.pop("DBUS_SESSION_BUS_ADDRESS", None)
    try:
        return subprocess.run(["systemctl", "--user", "show", unit, "-p", "ExecStart", "-p", "Environment",
                               "-p", "WorkingDirectory", "-p", "FragmentPath", "-p", "Description"],
                              capture_output=True, text=True, timeout=120, env=env,
                              stdin=subprocess.DEVNULL).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def unconfined_places(base):
    """The shared locations of AC3, each with the depth it is read to and its rule (see the note at
    the top of this section). They are the owner's own, never taken from the leg's environment."""
    import pwd
    uid = os.getuid()
    home = Path(pwd.getpwuid(uid).pw_dir)
    return [
        {"name": "systemd configuration", "path": home / ".config/systemd/user", "depth": 2, "rule": "strict"},
        {"name": "runtime directory", "path": Path("/run/user/%d" % uid), "depth": 1, "rule": "strict"},
        {"name": "/dev/shm", "path": Path("/dev/shm"), "depth": 1, "rule": "strict"},
        {"name": "temporary directory", "path": Path(base).parent, "depth": 1, "rule": "attributed"},
        {"name": "owner cache", "path": home / ".cache/veldo", "depth": 1, "rule": "strict"},
        {"name": "owner state", "path": home / ".local/state/veldo", "depth": 1, "rule": "strict"},
    ]


def confined_places(base, environ):
    """What a confined shard could reach outside its roots if its layer failed: the leg's own home
    and the directory the shards' roots stand in. Attributed: outside the gate's launcher these are
    the owner's home and /tmp, which other sessions write."""
    places = [{"name": "leg temporary directory", "path": Path(base).parent, "depth": 1, "rule": "attributed"}]
    if environ.get("HOME"):
        places.append({"name": "leg home", "path": Path(environ["HOME"]), "depth": 1, "rule": "attributed"})
    return places


def _listing(path, depth):
    names = set()
    try:
        entries = list(os.scandir(str(path)))
    except OSError:
        return names
    for entry in entries:
        names.add(entry.name)
        if depth > 1:
            try:
                inner = entry.is_dir(follow_symlinks=False)
            except OSError:
                inner = False
            if inner:
                names.update(entry.name + "/" + n for n in _listing(entry.path, depth - 1))
    return names


class SharedPlaces:
    """One reading of every shared place, and of the user manager's units when a lister is given."""

    def __init__(self, places, units=None, describe=None):
        self.places, self.units, self.describe = list(places), units, describe
        self.answers = True  # False once the manager, having answered before, stopped answering

    def read(self):
        seen = set()
        for place in self.places:
            seen.update((place["name"], item) for item in _listing(place["path"], place["depth"]))
        if self.units is not None:
            listed = self.units()
            if listed is None:
                self.answers = False
            else:
                seen.update(("unit", name) for name in listed)
        return seen

    def place(self, name):
        return next((p for p in self.places if p["name"] == name), None)


def _holders(path):
    """[(pid, environment text)] of live processes whose working directory or an open descriptor
    lies at or beneath `path`. Another account's processes are unreadable and are not listed."""
    target = str(path)
    found = []
    for name in os.listdir("/proc"):
        if not name.isdigit() or int(name) == os.getpid():
            continue
        held = False
        try:
            links = [os.readlink("/proc/%s/cwd" % name)]
            links += [os.readlink("/proc/%s/fd/%s" % (name, fd)) for fd in os.listdir("/proc/%s/fd" % name)]
        except OSError:
            links = []
        for link in links:
            if link == target or link.startswith(target + "/"):
                held = True
                break
        if held:
            try:
                environment = Path("/proc/%s/environ" % name).read_bytes().decode("utf-8", "replace")
            except OSError:
                environment = ""
            found.append((int(name), environment))
    return found


def _shard_named(text, base, jobs):
    """The suite whose roots `text` mentions, or None."""
    for job in jobs:
        roots = job.get("roots") or {v: str(p) for v, p in shard_roots(base, job["index"])[1].items()}
        for path in set(roots.values()):
            if path in text and re.search(re.escape(path) + r"(?![0-9A-Za-z_.-])", text):
                return job["name"]
    return None


def attribute(kind, item, path, base, jobs, describe=None):
    """Whose a new item is: (suite or None, 'leg' | 'foreign' | 'unknown', how it was told).
    See the note at the top of this section for what each answer rests on."""
    # By name: the engine names what it creates with the suite's instance name.
    for job in sorted(jobs, key=lambda j: -len(j["name"])):
        if job["name"] in item:
            return job["name"], "leg", "its name carries the suite's instance name"
    if kind == "unit":
        text = (describe or (lambda unit: ""))(item)
        named = _shard_named(text, base, jobs)
        if named or str(base) in text:
            return named, "leg", "the unit refers to a shard's roots"
        return None, "unknown", ""
    try:
        info = os.lstat(path)
    except OSError:
        return None, "unknown", ""
    if info.st_uid != os.getuid():
        return None, "foreign", "another account owns it"
    reference = ""
    try:
        if os.path.islink(path):
            reference = os.readlink(path)
        elif os.path.isfile(path) and info.st_size <= (1 << 20):
            reference = Path(path).read_bytes().decode("utf-8", "replace")
    except OSError:
        reference = ""
    named = _shard_named(reference, base, jobs)
    if named or str(base) in reference:
        return named, "leg", "it refers to a shard's roots"
    holders = _holders(path)
    for _pid, environment in holders:
        named = _shard_named(environment, base, jobs)
        if named or str(base) in environment:
            return named, "leg", "a process that carries a shard's roots holds it"
    if holders:
        return None, "foreign", "a live process of another tree holds it (pid %d)" % holders[0][0]
    return None, "unknown", ""


# ---- the dispatcher ----------------------------------------------------------------------------

class ShardsStopped(Exception):
    """The dispatcher was told to stop (TERM, INT or HUP): every shard is ended first."""

    def __init__(self, number):
        super().__init__("signal %d" % number)
        self.number = number


def _drain(descriptor):
    """Everything a non-blocking descriptor holds now, and whether its writers are gone."""
    data = b""
    while True:
        try:
            chunk = os.read(descriptor, 65536)
        except BlockingIOError:
            return data, False
        except OSError:
            return data, True
        if not chunk:
            return data, True
        data += chunk


def _group_anonymous(groups):
    """{process group: anonymous resident bytes of its members now}, read from /proc."""
    totals = dict.fromkeys(groups, 0)
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        try:
            stat = Path("/proc/%s/stat" % name).read_text()
            group = int(stat.rsplit(")", 1)[1].split()[2])
            if group not in totals:
                continue
            for line in Path("/proc/%s/status" % name).read_text().splitlines():
                if line.startswith("RssAnon:"):
                    totals[group] += int(line.split()[1]) * 1024
                    break
        except (OSError, ValueError, IndexError):
            continue
    return totals


def shard_verdict(job, leg, status):
    """Read one ended shard: its counts, and every way it failed its suite (codes of
    SHARD_FAILURES, each with the words a reader needs). Nothing here trusts the exit status alone
    or the report alone: they must agree."""
    records = []
    for line in job["report"].decode("utf-8", "replace").splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict):
            records.append(record)
    events = [r.get("event") for r in records]
    verdict = next((r for r in records if r.get("event") == "verdict" and r.get("suite") == job["name"]), None)
    failures = []
    passed = failed = 0
    rows = []
    if job.get("timed_out"):
        failures.append(("deadline_exceeded", "it ran past its deadline of %.0fs and was ended" % job["deadline"]))
        verdict = None
    elif verdict is None:
        code = os.waitstatus_to_exitcode(status) if status is not None else None
        failures.append(("no_verdict", "its process ended (exit %s) without reporting a verdict" % code))
    if verdict is not None:
        try:
            passed, failed = int(verdict["passed"]), int(verdict["failed"])
            rows = list(verdict["rows"])
            before = int(verdict["prerequisite_failed"])
        except (KeyError, TypeError, ValueError):
            failures.append(("no_verdict", "its verdict record is not the dispatcher's form"))
            verdict, passed, failed, rows, before = None, 0, 0, [], 0
    if verdict is not None:
        if passed + failed == 0 or len(rows) != passed + failed:
            failures.append(("asserted_nothing", "its target asserted %d row(s) and named %d"
                             % (passed + failed, len(rows))))
        if before:
            failures.append(("prerequisite_failed", "%d row(s) of its closure or of the shared preamble "
                             "failed before its target ran" % before))
        expected = PARTIAL_FAILED_EXIT if failed or before else PARTIAL_PASSED_EXIT
        code = os.waitstatus_to_exitcode(status)
        if code != expected:
            failures.append(("exit_status", "it exited %d where its verdict means %d" % (code, expected)))
    layer = None
    if leg == "confined" and job["name"] in UNLAYERED:
        layer = {"exempt": True}
    elif leg == "confined":
        layer = next((r for r in records if r.get("event") == "layer"), None)
        target_at = events.index("target") if "target" in events else len(events)
        problem = None
        if layer is None or events.index("layer") > target_at:
            problem = "it reported no Landlock layer before its suite ran"
        elif not (layer.get("in_force") is True and layer.get("refused") is True):
            problem = "its Landlock layer was not in force (%s)" % (layer.get("detail") or "no refusal")
        elif os.path.lexists(str(shard_probe(job["root"]))):
            problem = "its probe outside its roots was written"
        if problem:
            failures.append((ISOLATION_BREACH, problem))
    mark = next((r.get("mark") for r in records if r.get("event") == "target"), None)
    return {"passed": passed, "failed": failed, "rows": rows, "failures": failures, "mark": mark,
            "verdict": verdict is not None, "layer": layer}


def relay(job, result):
    """A shard's own output as the leg prints it. A failed row is printed as the ordered run would
    print it only where it is COUNTED: a row of the target, in a shard that reported a verdict. A
    failed row of a prerequisite or of the shared preamble belongs to that suite's own shard, and
    a shard with no verdict counts once, so their lines are kept and marked uncounted. The gate's
    first-use check requires the printed failure names and the counted failures to be one set."""
    text = job["output"].decode("utf-8", "replace")
    lines = text.splitlines()
    at = lines.index(result["mark"]) if result["mark"] in lines else None
    printed = []
    for number, line in enumerate(lines):
        if at is not None and number == at:
            continue
        counted = result["verdict"] and at is not None and number > at
        if FAIL_MARK in line and not counted:
            line = line.replace(FAIL_MARK, UNCOUNTED_MARK)
        printed.append(line)
    return printed


def run_shards(root, leg, targets, *, environ=None, emit=None, requires=None, manifest=None,
               places=None, units=manager_units, describe=describe_unit, deadline=SHARD_DEADLINE_S,
               settle=SETTLE_S, parallel=None, python=None, tick=SHARD_TICK_S):
    """Run one gate leg as shards and return what it proved: {passed, failed, shards, breaches,
    parallelism, events, wall_seconds}. `targets` are the leg's suites by name, each a target
    exactly once. Green is failed == 0, which needs every shard to pass and the isolation check to
    hold. The keyword arguments after `environ` exist for a fixture leg: the real gate passes none.
    """
    # Every shard's roots stand in one temporary directory of this leg's own, which ends with it.
    with tempfile.TemporaryDirectory(prefix="s", ignore_cleanup_errors=True) as directory:
        return _run_shards(Path(directory), Path(root), leg, targets, environ, emit, requires, manifest,
                           places, units, describe, deadline, settle, parallel, python, tick)


def _run_shards(base, root, leg, targets, environ, emit, requires, manifest, places, units, describe,
                deadline, settle, parallel, python, tick):
    environ = dict(os.environ if environ is None else environ)
    say = emit or (lambda line: print(line, flush=True))
    manifest = manifest or load_manifest(root / "scripts" / "suites" / "manifest.json")
    if requires is None:
        requires = load_requires(root / "scripts" / "suites" / "requires.json")
    order = [s["name"] for s in fragments(manifest)]
    resources = ShardResources(manifest)
    names = []
    for name in targets:
        if name not in names:
            names.append(name)
    claims = handed_claims(environ)
    began = time.monotonic()
    (base / SHARD_PROBES).mkdir(mode=0o700)
    jobs = []
    for index, name in enumerate(names):
        closure = requires.get(name)
        problem = None
        if not closure or name not in closure or any(n not in order for n in closure):
            problem = ("scripts/suites/requires.json carries no usable closure for it; regenerate with "
                       "`python3 scripts/run_scope.py --emit-requires`")
        jobs.append({"name": name, "index": index, "closure": [n for n in order if n in (closure or ())],
                     "problem": problem, "claim": claims.get(name, SHARD_UNMEASURED),
                     "root": shard_roots(base, index)[0], "output": b"", "report": b"", "peak": 0})
    # The longest measured shard first: it is the floor of the leg's wall time. Unmeasured ones keep
    # the manifest's order ahead of it, so a first run is the manifest's order.
    pending = sorted((j for j in jobs if not j["problem"]),
                     key=lambda j: -claims.get(j["name"], {"seconds": float("inf")})["seconds"])
    ledger = ShardLedger(environ[LEDGER_CHANNEL]) if environ.get(LEDGER_CHANNEL) else None
    parallelism = None if ledger else max(1, int(parallel or usable_cpus()))
    metrics = int(environ[SHARD_METRICS]) if environ.get(SHARD_METRICS, "").isdigit() else None
    if metrics is not None:
        try:
            os.set_blocking(metrics, False)  # a reader that fell behind loses a line, never holds the leg
        except OSError:
            metrics = None
    python = python or sys.executable
    passes = launcher_fds(root)
    scratch = leg_scratch(environ, root) if leg == "confined" else None
    # WHICH SHARDS GET THEIR INSTANCE NAME. Every shard of a confined leg. In an unconfined leg, only
    # a suite whose manifest entry declares `"instance": true`, and no suite of this repository
    # declares it yet: measured on 2026-11-21 against the real user manager, suites 66, 85 and 117
    # fail with an instance configured in their shard (their own fixtures hand their subprocesses a
    # configuration root of their own, so the installer and the tool it starts disagree on the
    # unit's name, and 66 pins the installation's exact file set). The suites are outside
    # VELDO-0221, so until they carry the name through their fixtures the unconfined leg's units
    # keep today's names, apart on the one manager as they are in the mutation stage: by each
    # installation's own service id and by the manifest's manager declarations.
    named = {s["name"] for s in fragments(manifest) if s.get("instance") is True}
    own = set()  # what this dispatcher itself made outside its own directory
    # THE ISOLATION CHECK RUNS IN EVERY GATE (owner decision D1): nothing here reads whether this
    # gate was asked to be force-fresh.
    if places is None:
        places = confined_places(base, environ) if leg == "confined" else unconfined_places(base)
    watch = SharedPlaces(places, units if leg != "confined" else None, describe)
    before = watch.read()
    watched_units = watch.answers and watch.units is not None
    known, first_seen, window = set(before), {}, set()
    running, done, events = {}, [], []
    selector = selectors.DefaultSelector()
    stopped = []

    def stop(number, _frame):
        raise ShardsStopped(number)
    previous = {n: signal.signal(n, stop) for n in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)}

    def observe():
        nonlocal window
        seen = watch.read()
        suspects = sorted(window | set(running))
        for item in seen - known:
            first_seen[item] = suspects
        known.update(seen)
        window = set(running)
        return seen

    def launch(job):
        directory, roots = shard_roots(base, job["index"])
        short = short_temporary(scratch) if scratch is not None else None
        if short is not None:
            roots["TMPDIR"] = short
            own.add(str(short))
        for path in roots.values():
            if path != short:
                path.mkdir(mode=0o700)
        linked = link_manager(roots["XDG_RUNTIME_DIR"], "/run/user/%d" % os.getuid())
        if leg == "confined" or job["name"] in named:
            write_instance(roots["XDG_CONFIG_HOME"], job["name"])
        env = shard_environment(environ, roots, linked, base)
        report_r, report_w = os.pipe()
        output_r, output_w = os.pipe()
        try:
            process = subprocess.Popen(
                [python, str(root / "scripts" / "selftest.py"), "--suite", job["name"],
                 SHARD_ARGUMENTS[0], str(report_w), SHARD_ARGUMENTS[1], str(directory)],
                env=env, stdin=subprocess.DEVNULL, stdout=output_w, stderr=output_w,
                pass_fds=(report_w, *passes), process_group=0)
        finally:
            os.close(report_w)
            os.close(output_w)
        for descriptor in (report_r, output_r):
            os.set_blocking(descriptor, False)
        job.update(pid=process.pid, process=process, started=time.monotonic(), deadline=deadline,
                   pidfd=os.pidfd_open(process.pid), report_fd=report_r, output_fd=output_r,
                   roots={k: str(v) for k, v in roots.items()}, linked=linked)
        selector.register(report_r, selectors.EVENT_READ, ("report", job))
        selector.register(output_r, selectors.EVENT_READ, ("output", job))
        selector.register(job["pidfd"], selectors.EVENT_READ, ("exit", job))
        events.append({"event": "start", "suite": job["name"], "running": sorted(running),
                       "exclusive": resources.exclusive(job["name"]),
                       "resources": dict(resources.demand(job["name"]))})
        running[job["name"]] = job
        window.add(job["name"])

    def admit():
        barred = set()
        for job in list(pending):
            name = job["name"]
            demand = set(resources.demand(name))
            if barred & demand or not resources.fits(name):
                barred |= demand
                continue
            if ledger is None:
                if len(running) >= parallelism:
                    return
            elif not ledger.acquire(name, job["claim"]):
                return
            resources.acquire(name)
            pending.remove(job)
            try:
                launch(job)
            except BaseException:
                resources.release(name)
                if ledger is not None:
                    ledger.release(name)
                raise
            if ledger is not None:
                ledger.peak = max(ledger.peak, len(running))

    def finish(job, status, usage):
        for key in ("report_fd", "output_fd", "pidfd"):
            try:
                selector.unregister(job[key])
            except (KeyError, ValueError):
                pass
        # What is left of its process group ends with it: nothing of a shard runs on into another's.
        try:
            os.killpg(job["pid"], signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        job["report"] += _drain(job["report_fd"])[0]
        job["output"] += _drain(job["output_fd"])[0]
        for key in ("report_fd", "output_fd", "pidfd"):
            os.close(job[key])
        job["process"].returncode = os.waitstatus_to_exitcode(status)
        wall = time.monotonic() - job["started"]
        cpu = usage.ru_utime + usage.ru_stime
        job.update(wall_seconds=wall, cpu_seconds=cpu,
                   peak_anon_bytes=max(job["peak"], usage.ru_maxrss * 1024))
        result = shard_verdict(job, leg, status)
        del running[job["name"]]
        resources.release(job["name"])
        if ledger is not None:
            ledger.release(job["name"])
        events.append({"event": "end", "suite": job["name"], "running": sorted(running)})
        observe()
        job["result"] = result
        done.append(job)
        say("selftest shard %s %s: closure %s; roots %s*%s; %d passed, %d failed; wall %.1fs cpu %.1fs peak %d MiB%s"
            % (shard_tag(job["index"]), job["name"], ", ".join(job["closure"]), job["root"],
               "" if job["roots"]["TMPDIR"] == str(job["root"]) else " and " + job["roots"]["TMPDIR"], result["passed"],
               result["failed"], wall, cpu, job["peak_anon_bytes"] >> 20,
               "; Landlock layer in force" if result["layer"] and result["layer"].get("in_force") is True
               and result["layer"].get("refused") is True
               else "; NO Landlock layer of its own (exempt in run_scope.UNLAYERED)"
               if result["layer"] and result["layer"].get("exempt") else ""))
        for line in relay(job, result):
            say(line)
        if metrics is not None and result["verdict"] and not result["failures"] and not result["failed"]:
            try:
                os.write(metrics, (json.dumps({"suite": job["name"], "wall_seconds": wall, "cpu_seconds": cpu,
                                               "peak_anon_bytes": job["peak_anon_bytes"]}) + "\n").encode())
            except OSError:
                pass

    try:
        try:
            last_sample = time.monotonic()
            while pending or running:
                admit()
                if not running and pending and ledger is None:
                    raise LegRefused("no pending shard fits the manifest's declared resources: %s"
                                     % ", ".join(j["name"] for j in pending))
                now = time.monotonic()
                wait = min([tick] + [j["started"] + j["deadline"] - now for j in running.values()])
                for key, _mask in selector.select(max(0.0, wait)):
                    kind, job = key.data
                    if kind == "exit":
                        _pid, status, usage = os.wait4(job["pid"], 0)
                        finish(job, status, usage)
                        continue
                    data, closed = _drain(key.fd)
                    job[kind] += data
                    if closed:
                        selector.unregister(key.fd)
                now = time.monotonic()
                for job in list(running.values()):
                    if now - job["started"] > job["deadline"] and not job.get("timed_out"):
                        job["timed_out"] = True
                        try:
                            os.killpg(job["pid"], signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                if running and now - last_sample >= tick:
                    last_sample = now
                    for group, total in _group_anonymous({j["pid"] for j in running.values()}).items():
                        for job in running.values():
                            if job["pid"] == group:
                                job["peak"] = max(job["peak"], total)
        except ShardsStopped as error:
            stopped.append(error.number)
        finally:
            for job in list(running.values()):
                try:
                    os.killpg(job["pid"], signal.SIGKILL)
                except ProcessLookupError:
                    pass
                try:
                    os.wait4(job["pid"], 0)
                except ChildProcessError:
                    pass
                if ledger is not None:
                    try:
                        ledger.release(job["name"])
                    except (OSError, ValueError, LegRefused):
                        pass
        if stopped:
            raise ShardsStopped(stopped[0])

        # ---- what each shard proved --------------------------------------------------------------
        passed = failed = 0
        charged = {}  # suite -> [(code, words)]
        for job in jobs:
            if job["problem"]:
                charged.setdefault(job["name"], []).append(("closure_unavailable", job["problem"]))
                continue
            result = job["result"]
            passed += result["passed"]
            failed += result["failed"]
            for failure in result["failures"]:
                charged.setdefault(job["name"], []).append(failure)

        # ---- the isolation check, in every gate --------------------------------------------------
        breaches, unattributed = [], []
        after = observe()
        if watched_units and not watch.answers:
            breaches.append((None, "the user manager answered before the leg and not after it, so its "
                                   "units could not be checked"))
        candidates = {}
        for kind, item in sorted(after - before):
            place = watch.place(kind)
            if place is not None and (Path(place["path"]) / item == base or str(Path(place["path"]) / item) in own):
                continue
            candidates[(kind, item)] = place
        waiting = {}
        for (kind, item), place in candidates.items():
            path = (Path(place["path"]) / item) if place else None
            suite, whose, how = attribute(kind, item, path, base, jobs, watch.describe)
            where = "unit %s" % item if kind == "unit" else "%s: %s" % (kind, path)
            suspects = first_seen.get((kind, item)) or []
            if whose == "leg":
                breaches.append((suite, "%s was left behind (%s)" % (where, how), suspects))
            elif whose == "foreign":
                unattributed.append("%s (%s)" % (where, how))
            elif place is not None and place["rule"] == "attributed":
                unattributed.append("%s (nothing ties it to a shard)" % where)
            else:
                waiting[(kind, item)] = (where, suspects)
        limit = time.monotonic() + settle
        while waiting and time.monotonic() < limit:
            time.sleep(min(1.0, max(0.0, limit - time.monotonic())))
            present = watch.read()
            for key in [k for k in waiting if k not in present]:
                unattributed.append("%s (gone again %.0fs after the leg)"
                                    % (waiting.pop(key)[0], settle - (limit - time.monotonic())))
        for (kind, item), (where, suspects) in sorted(waiting.items()):
            breaches.append((None, "%s appeared during the leg and was left behind%s"
                             % (where, "" if kind != "unit" else ", and carries no shard's prefix"),
                             suspects))
        for breach in breaches:
            suite, words = breach[0], breach[1]
            suspects = breach[2] if len(breach) > 2 else []
            owners = [suite] if suite else (suspects or [j["name"] for j in jobs])
            for owner in owners:
                if not any(code == ISOLATION_BREACH and text == words for code, text in charged.get(owner, [])):
                    charged.setdefault(owner, []).append((ISOLATION_BREACH, words))

        # ---- one counted failure per shard-level failure, each with a fixed name ------------------
        for job in jobs:
            for code, words in charged.get(job["name"], []):
                failed += 1
                say("  %s suite-shard %s %s" % (FAIL_MARK, job["name"], code))
                say("     %s: %s" % (code, words))
        wall = time.monotonic() - began
        critical = max((j for j in jobs if "wall_seconds" in j), key=lambda j: j["wall_seconds"], default=None)
        isolation = [w for owner in charged.values() for code, w in owner if code == ISOLATION_BREACH]
        say("selftest leg %s: %d shard(s), parallelism %s, peak %d running; isolation check %s; critical shard %s; wall %.1fs"
            % (leg, len(jobs),
               "as the gate ledger grants" if ledger else "%d (no gate ledger: this host's usable cores)" % parallelism,
               max([len(e["running"]) + 1 for e in events if e["event"] == "start"] or [0]),
               "held" if not isolation else "FAILED: %s" % ISOLATION_BREACH,
               "%s %.1fs" % (critical["name"], critical["wall_seconds"]) if critical else "none", wall))
        for line in unattributed:
            say("   isolation note, not charged: %s" % line)
        for job in jobs:
            if leg == "confined" and job["name"] in UNLAYERED:
                say("   shard %s ran without a Landlock layer of its own: %s" % (job["name"], UNLAYERED[job["name"]]))
        return {"passed": passed, "failed": failed, "targets": names, "charged": charged,
                "breaches": isolation, "unattributed": unattributed, "events": events,
                "parallelism": parallelism, "wall_seconds": wall,
                "shards": [{k: j.get(k) for k in ("name", "index", "closure", "wall_seconds", "cpu_seconds",
                                                    "peak_anon_bytes", "roots", "linked", "claim")}
                           | {"passed": j["result"]["passed"] if "result" in j else 0,
                              "failed": j["result"]["failed"] if "result" in j else 0}
                           for j in jobs]}
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)
        selector.close()
        if ledger is not None:
            ledger.close()


def full_scope(manifest=None):
    """The scope of a run with NO selector: the whole manifest, allowed to claim."""
    manifest = manifest or load_manifest()
    names = [s["name"] for s in fragments(manifest)]
    return RunScope(None, names, names)


def main(argv):
    # --output PATH writes the table elsewhere: the freshness check regenerates into a private
    # path and compares, so it never writes the tree it verifies.
    if argv[1:2] == ["--emit-requires"] and (len(argv) == 2 or (len(argv) == 4 and argv[2] == "--output")):
        doc = requires_document()
        target = Path(argv[3]) if len(argv) == 4 else REQUIRES_PATH
        target.write_text(json.dumps(doc, indent=1) + "\n")
        print("run_scope: wrote %s (%d suites)" % (target, len(doc["requires"])))
        return 0
    print(__doc__.strip().splitlines()[0])
    print("usage: run_scope.py --emit-requires [--output PATH]")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
