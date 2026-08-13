#!/usr/bin/env python3
"""Cost-to-change per area (WARP-1409, W9 of PLAN-0014): the per-area aggregation of the
Tokens of Effort actuals corpus, with the JOIN THAT PRODUCED EVERY NUMBER NAMED IN THE DATA.

WHAT THIS IS. PLAN-0011's entropy organ asks a question this plan's corpus can answer: what
does a change to this area actually cost. This module answers it by aggregating the per-spec
actuals records WARP-1401 derives (veldo.toe_actuals/v1) onto the areas the architecture
contract declares, and by reporting, per record and per area, WHICH JOIN put it there.

TWO JOINS, AND THE WEAKER ONE SAYS SO IN THE DATA.

  placement - the spec declares a placement (with its footprint) that RESOLVES to declared
  contract areas. This is PLAN-0011's W3 declaration and it is the join that means something,
  because a human said where the change lands.

  git_path - the spec declares no placement the contract resolves, so the areas are the ones
  the files GIT SAYS the change touched fall into. This is a STAND-DOWN and not an equivalent.
  It is derived from what happened rather than from what was declared; it sees only paths some
  area's includes globs enumerate; and it cannot see a change whose commits never named the
  spec. Every record attributed this way carries `basis: git_path` and a label that spells the
  weakness out, every area carries a per-basis count, and the report carries a notice. IN THE
  DATA, NOT IN A COMMENT: a reader of the JSON never sees a comment, and this is the whole
  reason the field exists rather than a docstring sentence.

  Anything else is UNATTRIBUTED and counted as such. NOTHING IS EVER SPREAD, SPLIT, GUESSED OR
  DEFAULTED INTO AN AREA. A fabricated join is the one failure this item cannot have: a cost
  attributed to the wrong area is worse than a missing one, because the missing one is visible
  and the wrong one is authoritative.

THE COST FIELDS ARE UNKNOWN IN THIS REPOSITORY AND THE REPORT SAYS SO RATHER THAN SUMMING TO
ZERO. WARP-1401 measured it: 904 events, not one carrying `tokens`, `cost_usd` or
`human_minutes`, because a token count is not knowable from inside a repository. So an area
whose records carry no recorded spend reports its cost fields as None with `cost_known` false
and `spend_coverage` 0.0, NEVER as a confident zero.

AND NOTHING RECORDED IS ABSENT FROM EVERY FIGURE, which is the other half of that sentence and was
missing. The per-area cost is summed over an area's own members, so a record attributed to NO area
reached no cost field anywhere: recording spend against an unattributed spec turned the corpus-level
`usable_as_cost_ground_truth` true, suppressed the notice that explains the Nones, and reported the
tokens nowhere at all. The blunt booleans are statements about the PER-AREA figures and therefore
count the records that reached an area (`cost_attributed_records`, `gate_attributed_records`); the
remainder is reported as `cost_unattributed_records` with its own notice; and the unattributed bucket
carries its own cost and cycles blocks, so a figure a reader cannot audit does not exist here.

AND THE SAME DISCIPLINE APPLIES TO THE GATE CYCLES, BECAUSE THEY ARE UNRECORDED HERE TOO. The
two cycle signals are NOT one signal and are not equally available: review verdicts carry the
spec they belong to, but scripts/verify.sh writes its gate.passed and gate.failed events with a
COMMIT and no spec id or correlation id, and toe_corpus.cycles_for joins on exactly those ids,
so no gate run in this repository can reach a spec. `gate_passes=0` for every area would
therefore be an ABSENCE printed as a measurement, and a reader quoting "this area had zero gate
failures" would be quoting the emitter gap. So gate_passes and gate_failures are None with
`gate_basis` unrecorded and `gate_coverage` 0.0 when no record in the set carried a gate event,
review verdicts are counted separately with their own basis and coverage, and the report carries
a `cycle_notice` naming the emitter gap. That makes this map a per-area REVIEW-CYCLE map today,
a REWORK map the day the gate's own events name the spec they ran for, and a token map the day
something records spend (.veldo/spend.py). All three gaps are numbers in the data here, and
none of them is closed here.

THE SEAM TO THE ARCHITECTURE ORGAN IS PROSE, NEVER A DEPENDENCY EDGE (PLAN-0014 C6). This
module does not import .veldo/entropy.py and entropy.py does not import this one. Nothing in
either plan's contract declares an edge between them. What is shared is the RESOLUTION, not
the module: the areas come from .veldo/arch.py (footprint_areas for the declaration, and
area_for_path for the stand-down), which is the one place in this repository a placement or a
path becomes an area, so this map and the entropy map can never disagree about where a change
landed. Reading a spec's own front matter goes through the caller's parser, which is
validate.parse_yamlish, so there is no second parser here; going through entropy's index
instead would have created exactly the cross-plan dependency edge C6 forbids.

DEPENDENCY FREE BY CONSTRUCTION, the posture arch.py established: every function is pure over
data the caller passes in - the corpus, the parsed contract, the arch module, a front-matter
lookup and a touched-paths lookup. It reads no clock, mints no id, writes nothing and starts
no process. The CLI at the bottom is the only place the real corpus, the real contract and the
real git reader are wired together.

ADOPTION SAFE, AND THE STAND-DOWN IS SILENT. No architecture contract stands the whole
derivation down; no actuals records stands it down too. NO GATE STAGE CONSUMES THIS MODULE'S
OUTPUT, so nothing the gate runs can fail because a per-area cost map was unavailable, malformed
or slow, and a repository that never calls it is byte-identically unaffected. Said precisely,
because the earlier wording ("nothing in the gate calls this module") was not true: the one gate
stage that LOADS it is scripts/selftest.py, which executes this item's own suite, and a test
asserting a module's behaviour is the opposite of a stage trusting its numbers. The claim is
asserted over a domain DERIVED from scripts/verify.sh, not over a hand-typed file list.

FAIL CLOSED AND BY NAME. A malformed actuals record is REFUSED with a message naming the
record, the field and what is wrong with it, because a corpus that is quietly skipped produces
a smaller map that still looks complete.

  python3 .veldo/cost_to_change.py            # human-readable per-area cost-to-change
  python3 .veldo/cost_to_change.py --json     # machine-readable (the entropy organ's feed)
"""
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCHEMA = "veldo.cost_to_change/v1"

# The schema of the records this aggregates. WARP-1401 owns it; naming it here means a corpus
# of some other shape is refused rather than silently aggregated into a plausible-looking map.
CORPUS_SCHEMA = "veldo.toe_actuals/v1"

# The two joins and the honest third outcome. Closed vocabulary: a basis outside this set
# cannot be produced, so a consumer switching on it has a complete set of cases.
BY_PLACEMENT = "placement"
BY_GIT_PATH = "git_path"
UNATTRIBUTED = "unattributed"
BASES = (BY_PLACEMENT, BY_GIT_PATH, UNATTRIBUTED)

# WHAT EACH BASIS MEANS, carried in the report so the weakness travels with the number. The
# git_path label is deliberately blunt: it is the sentence a reader needs before quoting a
# per-area figure that no human ever declared.
BASIS_LABELS = {
    BY_PLACEMENT: ("joined on the spec's DECLARED placement (PLAN-0011 W3 declaration "
                   "present and resolving to contract areas)"),
    BY_GIT_PATH: ("ATTRIBUTED BY GIT PATH, NOT BY A DECLARATION: this spec declares no "
                  "placement that resolves to a contract area, so its areas are the ones the "
                  "files git says the change touched fall into. Weaker than a placement: "
                  "derived from what happened rather than declared, blind to paths no area's "
                  "includes glob enumerates, and blind to commits that never named the spec"),
    UNATTRIBUTED: ("NO AREA: no resolving placement and no touched path inside a declared "
                   "area, so this record is counted and never assigned. Nothing is spread, "
                   "split or defaulted into an area"),
}

# THE TOP-LEVEL KEYS A REPORT CARRIES ONLY WHEN THE CONDITION THEY DISCLOSE IS PRESENT, enumerated
# ONCE. The stand-down promises a consumer the same key shape a live report carries, and that promise
# is stated as an equality against THIS set: a second spelling of "which keys are conditional" is how
# a notice gets added to the live report and forgotten in the stand-down, which is exactly the drift
# that comparison exists to catch.
CONDITIONAL_KEYS = ("notice", "cost_notice", "cycle_notice",
                    "unattributed_spend_notice", "unattributed_cycle_notice")

# The recorded spend fields, which are UNKNOWN rather than zero in a repository whose loop
# emits none of them, and the cycle fields, which are TWO SIGNALS rather than one.
COST_FIELDS = ("tokens", "cost_usd", "human_minutes")
# The gate half comes from an emitter that names no spec (verify.sh writes a commit), so it is
# separately knowable-or-not from the review half, whose emitter does name the spec. Splitting the
# groups here is what lets one of them be None while the other is a real number: a single
# CYCLE_FIELDS tuple could only be all-known or all-unknown, and that is how a confident zero got
# printed for every area in the first place.
GATE_CYCLE_FIELDS = ("gate_passes", "gate_failures")
REVIEW_CYCLE_FIELDS = ("review_verdicts",)
# The union, in its established order: the record validator and every consumer read this name.
CYCLE_FIELDS = GATE_CYCLE_FIELDS + REVIEW_CYCLE_FIELDS


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def record_problems(rec, where):
    """Every problem with ONE actuals record, as a list of messages that each NAME the record,
    the field and what is wrong. Empty means aggregatable.

    Fail closed by name rather than skip: a record dropped for being malformed produces a
    smaller per-area map that still looks complete, and a per-area cost is exactly the kind of
    number somebody quotes without asking how many records it came from."""
    out = []
    if not isinstance(rec, dict):
        return ["%s: an actuals record must be a mapping, got %s" % (where, type(rec).__name__)]
    spec = rec.get("spec")
    if not _is_str(spec):
        out.append("%s: record must name the spec it accounts for in `spec`, got %r"
                   % (where, spec))
    named = "%s (spec %s)" % (where, spec if _is_str(spec) else "unnamed")
    if rec.get("schema") != CORPUS_SCHEMA:
        out.append("%s: schema must be %r (this aggregation reads the WARP-1401 actuals "
                   "corpus and nothing else), got %r" % (named, CORPUS_SCHEMA,
                                                         rec.get("schema")))
    for block, fields in (("cycles", CYCLE_FIELDS), ("spend", COST_FIELDS)):
        got = rec.get(block)
        if not isinstance(got, dict):
            out.append("%s: %s must be a mapping, got %s"
                       % (named, block, type(got).__name__))
            continue
        for f in fields:
            v = got.get(f)
            if not _is_num(v):
                out.append("%s: %s.%s must be a number, got %r" % (named, block, f, v))
            elif v < 0:
                out.append("%s: %s.%s cannot be negative, got %r" % (named, block, f, v))
    cycles = rec.get("cycles")
    if isinstance(cycles, dict) and not _is_num(cycles.get("events_seen")):
        out.append("%s: cycles.events_seen must be a number (it is what separates no cycle "
                   "data from zero cycles), got %r" % (named, cycles.get("events_seen")))
    spend = rec.get("spend")
    if isinstance(spend, dict) and not isinstance(spend.get("spend_recorded"), bool):
        out.append("%s: spend.spend_recorded must be a boolean (it is what separates a sum of "
                   "zero because nothing was spent from a sum of zero because nothing was "
                   "ever emitted), got %r" % (named, spend.get("spend_recorded")))
    return out


def corpus_problems(corpus):
    """EVERY problem with a whole corpus, as a list of messages. ONE enumeration, which both
    surfaces below use: the gate-shaped reporter and the hard refusal the aggregation runs. Two
    spellings of "what is wrong with this corpus" would disagree the first time one is updated,
    and this repository has a named rule about that."""
    if not isinstance(corpus, list):
        return ["the actuals corpus must be a list of records, got %s"
                % type(corpus).__name__]
    problems = []
    seen = {}
    for i, rec in enumerate(corpus):
        problems.extend(record_problems(rec, "record %d" % i))
        if isinstance(rec, dict) and _is_str(rec.get("spec")):
            seen.setdefault(rec["spec"], []).append(i)
    for spec in sorted(seen):
        if len(seen[spec]) > 1:
            problems.append("spec %s appears in %d records (indices %s): a duplicate would be "
                            "counted twice in every area it touches"
                            % (spec, len(seen[spec]), seen[spec]))
    return problems


def check_corpus(corpus, fail, name="toe actuals corpus"):
    """Report every problem in a corpus through the caller's fail(name, msg) reporter and
    return the error count, the shape every gate check in this repository uses. The reporter is
    injected (validate.fail) so this module adds no second failure channel, and the problems
    come from the one enumeration above so this surface and the refusal below cannot diverge."""
    return sum(fail(name, msg) for msg in corpus_problems(corpus))


def refuse_malformed(corpus):
    """Raise ValueError naming every problem, or return the corpus unchanged. The aggregation
    entry point calls this so a malformed corpus cannot produce a partial map: a map missing
    the records nobody could read looks exactly like a map of a smaller repository."""
    problems = corpus_problems(corpus)
    if problems:
        raise ValueError("refusing to aggregate cost-to-change: " + "; ".join(problems))
    return corpus


def front_matter_index(specs_dir, parse):
    """spec id -> parsed front matter, for every spec in a directory, THROUGH THE CALLER'S
    PARSER (validate.parse_yamlish), so placement and footprint arrive as real lists and this
    module ships no second parser. Slicing the front-matter block out of the file is not
    parsing it; the block itself is handed to `parse`.

    A spec whose front matter is outside the parser's subset is SKIPPED here rather than
    refused, because that is a spec-validation failure the contract validator already reports
    by name, and refusing it twice would make an unrelated malformed spec take this map down."""
    out = {}
    d = Path(specs_dir)
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*.md")):
        if p.name.startswith("TEMPLATE") or p.name == "index.md":
            continue
        m = re.match(r"^---\n(.*?)\n---", p.read_text(), re.S)
        if not m:
            continue
        try:
            fm = parse(m.group(1))
        except ValueError:
            continue
        if isinstance(fm, dict) and _is_str(fm.get("id")):
            out[fm["id"]] = fm
    return out


def attribute(rec, contract, arch, fm=None, paths=None):
    """The areas ONE actuals record belongs to, and the join that put it there.

    The declaration wins when it resolves: arch.footprint_areas over the spec's parsed front
    matter is PLAN-0011's own join key, and it already filters to areas the contract declares,
    so a placement naming an area that does not exist resolves to nothing and falls through to
    the stand-down rather than inventing a home for the change.

    The stand-down is arch.area_for_path over the paths git says the change touched, and it is
    LABELLED AS SUCH in the returned record. When neither yields an area the record is
    unattributed: it is counted, and it is never assigned."""
    spec = rec.get("spec") if isinstance(rec, dict) else None
    paths = list(paths or [])
    declared = sorted(arch.footprint_areas(fm, contract)) if isinstance(fm, dict) else []
    if declared:
        return {"spec": spec, "areas": declared, "basis": BY_PLACEMENT,
                "basis_label": BASIS_LABELS[BY_PLACEMENT], "paths_considered": len(paths)}
    hit = set()
    for p in paths:
        if _is_str(p):
            hit |= arch.area_for_path(p, contract)
    if hit:
        return {"spec": spec, "areas": sorted(hit), "basis": BY_GIT_PATH,
                "basis_label": BASIS_LABELS[BY_GIT_PATH], "paths_considered": len(paths)}
    return {"spec": spec, "areas": [], "basis": UNATTRIBUTED,
            "basis_label": BASIS_LABELS[UNATTRIBUTED], "paths_considered": len(paths)}


def _has_cycle_signal(cycles, fields):
    """Whether ONE record's cycles carried any of `fields` as a positive count. This is the only
    evidence available that the signal reached this record at all: the corpus record cannot
    distinguish a gate run that happened and named no spec from a gate run that never happened, so
    "some record in this set carried one" is what separates a measured zero from an absence."""
    return any(_is_num(cycles.get(f)) and cycles[f] > 0 for f in fields)


def _sum_cycles(records):
    """Recorded cycles for a set of records, PER SIGNAL, with the unrecorded signal reported as
    None rather than as zero.

    Gate failures stay separate from passes: a change that went red three times before green cost
    three gate runs, and a map that merged them could not show rework at all. But the two of them
    together are separate from review verdicts for a different and harder reason, and it is the same
    reason _sum_cost returns None: THE GATE EMITTER NAMES NO SPEC. scripts/verify.sh appends
    gate.passed and gate.failed carrying a commit, and toe_corpus.cycles_for joins on spec_id or
    correlation_id, so in this repository every record's gate counts are 0 because the join found
    nothing - not because the gate never ran. Printing that 0 would be a confident zero with full
    coverage, which is exactly what this module refuses to do for spend.

    So each group is a number only when at least one record in the set actually carried that
    signal, `gate_basis` and `review_basis` say which of the two happened, and gate_coverage and
    verdict_coverage are counted separately from cycles_coverage - which a verdict alone satisfies,
    and which therefore read 1.0 for an area with no gate-cycle data at all."""
    sums = {f: 0 for f in CYCLE_FIELDS}
    known = 0
    gate_known = 0
    review_known = 0
    for r in records:
        c = r.get("cycles") or {}
        if _is_num(c.get("events_seen")) and c["events_seen"] > 0:
            known += 1
        if _has_cycle_signal(c, GATE_CYCLE_FIELDS):
            gate_known += 1
        if _has_cycle_signal(c, REVIEW_CYCLE_FIELDS):
            review_known += 1
        for f in CYCLE_FIELDS:
            sums[f] += c.get(f, 0)
    out = {}
    for fields, count in ((GATE_CYCLE_FIELDS, gate_known), (REVIEW_CYCLE_FIELDS, review_known)):
        for f in fields:
            out[f] = sums[f] if count else None
    out["cycles_known"] = known
    out["cycles_coverage"] = round(known / len(records), 4) if records else 0.0
    out["gate_events_known"] = gate_known
    out["gate_coverage"] = round(gate_known / len(records), 4) if records else 0.0
    out["gate_basis"] = "recorded" if gate_known else "unrecorded"
    out["verdicts_known"] = review_known
    out["verdict_coverage"] = round(review_known / len(records), 4) if records else 0.0
    out["review_basis"] = "recorded" if review_known else "unrecorded"
    return out


def _spend_recorded(rec):
    """Whether ONE record carried recorded spend. ONE spelling, because the per-area sum, the
    corpus-level coverage count and the unattributed bucket all ask this question and a second
    spelling of it would let them disagree about which records carry cost."""
    return bool((rec.get("spend") or {}).get("spend_recorded"))


def _sum_cost(records):
    """Recorded spend for a set of records, or None per field when NOTHING was recorded.

    THE None IS THE POINT and it is WARP-1401's finding carried forward: this repository's loop
    emits no tokens, no cost and no human minutes, so a sum here would be a confident zero
    presented as a measurement. A field is a number only when at least one record in the set
    actually carried spend, and `cost_known` says which of the two happened."""
    known = [r for r in records if _spend_recorded(r)]
    out = {}
    for f in COST_FIELDS:
        if not known:
            out[f] = None
            continue
        total = sum((r.get("spend") or {}).get(f, 0) for r in known)
        out[f] = round(float(total), 6) if f == "cost_usd" else total
    out["cost_known"] = bool(known)
    out["spend_known"] = len(known)
    out["spend_coverage"] = round(len(known) / len(records), 4) if records else 0.0
    out["cost_basis"] = "recorded" if known else "unrecorded"
    return out


def _unattributed_block(atts, records):
    """The unattributed bucket, WITH ITS OWN COST AND CYCLE BLOCKS in the shape an area carries.

    NOTHING RECORDED MAY BE ABSENT FROM EVERY FIGURE, and until this block existed something could
    be: the per-area cost is summed over an area's own members, so a record attributed to no area
    reached no cost field anywhere, and a corpus whose ONLY recorded spend sat on an unattributed
    spec reported that spend NOWHERE while the coverage block counted it. A reader cannot audit a
    number that is in no figure. The spend is still never spread, split or defaulted into an area -
    it is reported HERE, against the bucket that honestly holds no area."""
    return {
        "records": len(records),
        "specs": sorted(a["spec"] for a in atts if _is_str(a["spec"])),
        "reason": BASIS_LABELS[UNATTRIBUTED],
        "cycles": _sum_cycles(records),
        "cost": _sum_cost(records),
    }


def _coverage_block(corpus, attributed, unattributed, area_memberships):
    """Every coverage figure, for a live report and for a stand-down, from ONE enumeration.

    THE TWO BLUNT BOOLEANS ARE STATEMENTS ABOUT THE PER-AREA FIGURES, which is what a consumer of
    this map reads, so they count the records that REACHED an area. They were computed over the
    whole corpus, and one `.veldo/spend.py record` against an unattributed spec made the map
    contradict itself in the data: `usable_as_cost_ground_truth` true, the notice that explains the
    Nones suppressed by the same event, and every area still reporting tokens None. A blunt boolean
    claiming cost ground truth over a map with no cost in it is precisely the number this item
    exists to stop a reader quoting. So the corpus count, the attributed count and the
    recorded-but-unattributed remainder are all reported, and the boolean is the attributed one."""
    n = len(corpus)
    cost_all = sum(1 for r in corpus if _spend_recorded(r))
    cost_att = sum(1 for r in attributed if _spend_recorded(r))
    gate_all = sum(1 for r in corpus
                   if _has_cycle_signal(r.get("cycles") or {}, GATE_CYCLE_FIELDS))
    gate_att = sum(1 for r in attributed
                   if _has_cycle_signal(r.get("cycles") or {}, GATE_CYCLE_FIELDS))
    return {
        "records": n,
        "attributed": n - len(unattributed),
        "area_memberships": area_memberships,
        "cost_known_records": cost_all,
        "cost_attributed_records": cost_att,
        "cost_unattributed_records": cost_all - cost_att,
        "cost_coverage": round(cost_all / n, 4) if n else 0.0,
        "usable_as_cost_ground_truth": cost_att > 0,
        # The rework half of the same honesty: how many records carried a gate event at all, how
        # many of those reached an area, and the blunt boolean that says whether a gate figure in
        # this map means anything.
        "gate_event_records": gate_all,
        "gate_attributed_records": gate_att,
        "gate_unattributed_records": gate_all - gate_att,
        "usable_as_rework_ground_truth": gate_att > 0,
    }


def standdown(reason):
    """The stand-down report, in ONE shape with the same keys a live report carries, so a
    consumer reads `standdown` and never has to guess whether a key is missing or the value is
    genuinely empty. Built once for both stand-down conditions: two spellings of an empty
    report is how a consumer ends up handling one of them and not the other. The unattributed and
    coverage blocks come from the SAME two builders the live report uses, over empty input, so a
    figure added to either one cannot be forgotten here."""
    return {"schema": SCHEMA, "standdown": True, "reason": reason,
            "areas": {}, "unattributed": _unattributed_block([], []),
            "attribution": {b: 0 for b in BASES}, "bases": {},
            "git_path_attributed": False,
            "coverage": _coverage_block([], [], [], 0)}


def report(corpus, contract, arch, fm_of=None, paths_of=None):
    """The per-area cost-to-change map: the whole output of this item.

    corpus is the WARP-1401 actuals records; contract is the parsed veldo.arch/v1 contract (or
    None); arch is the .veldo/arch.py module; fm_of and paths_of are lookups from a spec id to
    its parsed front matter and to the paths git says its change touched. Every one is injected
    so this stays pure and drivable from seeded data, and so nothing here can reach for the
    real repository behind a caller's back.

    Deterministic and idempotent: same inputs, same report, every run. No clock, no id, no
    write.

    Adoption safe: no contract, or no records, stands the whole thing down silently."""
    if contract is None:
        return standdown("no architecture contract (adoption safe: a repository without one is "
                         "byte-identically unaffected)")
    if not corpus:
        return standdown("no toe actuals records (adoption safe: nothing to aggregate, and a "
                         "repository that records none is byte-identically unaffected)")
    refuse_malformed(corpus)
    fm_of = fm_of if fm_of is not None else (lambda _s: None)
    paths_of = paths_of if paths_of is not None else (lambda _s: [])

    attributions = []
    by_area = {}
    unattributed = []
    unattributed_recs = []
    attributed_recs = []
    for rec in corpus:
        spec = rec["spec"]
        att = attribute(rec, contract, arch, fm_of(spec), paths_of(spec))
        attributions.append(att)
        if not att["areas"]:
            unattributed.append(att)
            unattributed_recs.append(rec)
            continue
        attributed_recs.append(rec)
        # A change that touched two areas contributes its recorded cost to EACH of them: the
        # question is what a change to THIS area costs, and a cross-area change did cost that
        # for each area it crossed. Nothing is divided between them, because a split would be
        # an invented weighting.
        for a in att["areas"]:
            by_area.setdefault(a, []).append((rec, att))

    counts = {b: sum(1 for a in attributions if a["basis"] == b) for b in BASES}
    areas_out = {}
    for area in sorted(by_area):
        pairs = by_area[area]
        recs = [r for r, _a in pairs]
        per_basis = {b: sum(1 for _r, a in pairs if a["basis"] == b) for b in BASES
                     if any(a["basis"] == b for _r, a in pairs)}
        areas_out[area] = {
            "records": len(recs),
            "attribution": per_basis,
            "attribution_basis": (sorted(per_basis)[0] if len(per_basis) == 1 else "mixed"),
            "members": sorted(({"spec": a["spec"], "basis": a["basis"],
                                "basis_label": a["basis_label"]} for _r, a in pairs),
                              key=lambda m: (m["spec"] or "")),
            "cycles": _sum_cycles(recs),
            "cost": _sum_cost(recs),
        }
    out = {
        "schema": SCHEMA,
        "standdown": False,
        "areas": areas_out,
        "unattributed": _unattributed_block(unattributed, unattributed_recs),
        "attribution": counts,
        # Only the bases actually used, so the label a reader needs is present and the ones
        # that would not apply are absent rather than decorative.
        "bases": {b: BASIS_LABELS[b] for b in BASES if counts[b]},
        "git_path_attributed": counts[BY_GIT_PATH] > 0,
        "coverage": _coverage_block(corpus, attributed_recs, unattributed_recs,
                                    sum(len(a["areas"]) for a in attributions)),
    }
    if out["git_path_attributed"]:
        out["notice"] = ("%d of %d records are attributed BY GIT PATH rather than by a "
                         "declared placement: those areas are derived from what the commits "
                         "touched, not from what anybody declared. See bases.git_path."
                         % (counts[BY_GIT_PATH], len(corpus)))
    if not out["coverage"]["usable_as_cost_ground_truth"]:
        out["cost_notice"] = ("NO RECORD ATTRIBUTED TO AN AREA CARRIES SPEND, so every per-area "
                              "cost field is None rather than zero: this map is a CYCLES map "
                              "today and becomes a token map when something records spend "
                              "(.veldo/spend.py). WARP-1401 measured the gap.")
    # THE DISCLOSURE THAT MUST NOT VANISH WITH THE EVENT THAT CREATES IT. Recorded spend on a spec
    # no area holds is in NO per-area figure, and gating this on the cost notice would remove the
    # one sentence explaining that exactly when a reader most needs it, since the same record turns
    # the corpus-level count positive. It is its own key, present whenever the remainder is.
    if out["coverage"]["cost_unattributed_records"]:
        out["unattributed_spend_notice"] = (
            "%d of the %d record(s) carrying spend are UNATTRIBUTED (no resolving placement and no "
            "touched path inside a declared area), so their spend reaches NO per-area figure and is "
            "reported ONLY in unattributed.cost. usable_as_cost_ground_truth is a statement about "
            "the PER-AREA figures and counts cost_attributed_records alone."
            % (out["coverage"]["cost_unattributed_records"],
               out["coverage"]["cost_known_records"]))
    if out["coverage"]["gate_unattributed_records"]:
        out["unattributed_cycle_notice"] = (
            "%d of the %d record(s) carrying a gate event are UNATTRIBUTED, so their gate cycles "
            "reach NO per-area figure and are reported ONLY in unattributed.cycles. "
            "usable_as_rework_ground_truth counts gate_attributed_records alone."
            % (out["coverage"]["gate_unattributed_records"],
               out["coverage"]["gate_event_records"]))
    if not out["coverage"]["usable_as_rework_ground_truth"]:
        out["cycle_notice"] = ("NO RECORD ATTRIBUTED TO AN AREA CARRIES A GATE PASS OR A GATE "
                               "FAILURE, so gate_passes and gate_failures are None per area "
                               "rather than "
                               "zero and the cycle half of this map is REVIEW VERDICTS ONLY. THE "
                               "EMITTER IS THE GAP: scripts/verify.sh appends gate.passed and "
                               "gate.failed carrying a COMMIT and no spec id or correlation id, "
                               "and toe_corpus.cycles_for joins on exactly those ids, so no gate "
                               "run can reach a spec. A zero here would be that absence printed "
                               "as a measurement. The emitter is out of scope for WARP-1409 and "
                               "this map reports the gap rather than closing it.")
    return out


def render_text(rep):
    """The report as text, with every figure drawn straight from the report so a reader and a
    consumer of the JSON can never see two different numbers."""
    if rep.get("standdown"):
        return "VELDO cost-to-change: standing down (%s)" % rep.get("reason", "")
    lines = ["VELDO cost-to-change per area (from the TOE actuals corpus; advisory, never "
             "gates)",
             "=" * 74,
             "  records %d, attributed %d, unattributed %d (by placement %d, by git path %d)"
             % (rep["coverage"]["records"], rep["coverage"]["attributed"],
                rep["unattributed"]["records"], rep["attribution"][BY_PLACEMENT],
                rep["attribution"][BY_GIT_PATH])]
    if rep.get("notice"):
        lines.append("  NOTICE: %s" % rep["notice"])
    if rep.get("cost_notice"):
        lines.append("  COST: %s" % rep["cost_notice"])
    if rep.get("cycle_notice"):
        lines.append("  CYCLES: %s" % rep["cycle_notice"])
    if rep.get("unattributed_spend_notice"):
        lines.append("  UNATTRIBUTED SPEND: %s" % rep["unattributed_spend_notice"])
    if rep.get("unattributed_cycle_notice"):
        lines.append("  UNATTRIBUTED CYCLES: %s" % rep["unattributed_cycle_notice"])
    for area in sorted(rep["areas"]):
        a = rep["areas"][area]
        c, cost = a["cycles"], a["cost"]
        lines.append("  area %s: %d change(s), attribution %s"
                     % (area, a["records"], a["attribution_basis"]))
        # %s, not %d, and that is the whole point: an unrecorded gate signal prints None here the
        # same way an unrecorded token count does, so the text surface cannot show a confident zero
        # the JSON does not carry.
        lines.append("    cycles: gate_passes=%s gate_failures=%s (%s, gate events on %d of %d) "
                     "review_verdicts=%s (%s, verdicts on %d of %d); any cycle data on %d of %d"
                     % (c["gate_passes"], c["gate_failures"], c["gate_basis"],
                        c["gate_events_known"], a["records"],
                        c["review_verdicts"], c["review_basis"], c["verdicts_known"],
                        a["records"], c["cycles_known"], a["records"]))
        lines.append("    cost: tokens=%s cost_usd=%s human_minutes=%s (%s, spend on %d of %d)"
                     % (cost["tokens"], cost["cost_usd"], cost["human_minutes"],
                        cost["cost_basis"], cost["spend_known"], a["records"]))
        if a["attribution"].get(BY_GIT_PATH):
            lines.append("    %d of these are BY GIT PATH, not by a declared placement"
                         % a["attribution"][BY_GIT_PATH])
    if rep["unattributed"]["records"]:
        u = rep["unattributed"]
        lines.append("  unattributed (counted, never assigned): %d change(s): %s"
                     % (u["records"], ", ".join(u["specs"][:8])))
        # THE BUCKET'S OWN FIGURES, so nothing recorded is absent from every figure on the human
        # surface either. The basis leads and the coverage trails, a DIFFERENT shape from an area
        # line on purpose: these numbers belong to no area, and an area assertion looking for its
        # own substring must not be able to match here.
        lines.append("    unattributed cost: %s, tokens=%s cost_usd=%s human_minutes=%s "
                     "(spend on %d of %d)"
                     % (u["cost"]["cost_basis"], u["cost"]["tokens"], u["cost"]["cost_usd"],
                        u["cost"]["human_minutes"], u["cost"]["spend_known"], u["records"]))
        lines.append("    unattributed cycles: %s, gate_passes=%s gate_failures=%s "
                     "review_verdicts=%s (gate events on %d of %d)"
                     % (u["cycles"]["gate_basis"], u["cycles"]["gate_passes"],
                        u["cycles"]["gate_failures"], u["cycles"]["review_verdicts"],
                        u["cycles"]["gate_events_known"], u["records"]))
    return "\n".join(lines)


def _load(name, rel, root=None):
    """Load a sibling module by path, the way entropy.py, budget.py and dashboard.py do it:
    one canonical source, no reimplementation, no package layout assumed. Used only by the
    CLI below, so every function above stays pure over injected data.

    `root` IS THE TREE THE SIBLING IS LOADED FROM, and it is the whole of how repo_report honours
    its own root parameter. Each of these siblings resolves its own paths from its own module-level
    ROOT - metrics.LOG, toe_corpus.ROOT, policy_check's policy file - so loading them from the tree
    under report is what makes the event stream, the git history and the protected patterns come
    from THAT tree instead of from wherever this file happens to live. Threading a root argument
    into each of them instead would put a second spelling of "which tree" in three modules.

    AN ABSENT SIBLING IS NAMED, never a bare FileNotFoundError out of a report: a tree that does
    not carry the estimation layer is a state a caller can act on, and the CLI turns this into one
    line and exit 1 rather than a traceback."""
    base = Path(root or ROOT)
    p = base / rel
    if not p.is_file():
        raise ValueError(
            "cannot derive cost-to-change for %s: it does not carry %s. This derivation reads the "
            "estimation layer of the tree it reports on (validate, toe_corpus, metrics and "
            "policy_check under .veldo/), so a tree without those four modules has no map to "
            "produce rather than an empty one." % (base, rel))
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def repo_report(root=None, load=None):
    """This repository's own cost-to-change map: the CLI's one wiring point.

    The corpus comes from toe_corpus.build over the recorded event stream, the contract and the
    parser from validate (load_repo_contract is the single place a consumer obtains the parsed
    contract), the front matter through validate.parse_yamlish, and the touched paths from
    toe_corpus.git_touched, which is the ONE reader of what git says a spec's change touched.
    Nothing here is a second implementation of any of it.

    `load` is the module loader, defaulting to _load and injected for exactly one reason: THIS IS
    THE FUNCTION THAT PRODUCES EVERY NUMBER ANYBODY QUOTES, and every join it makes is invisible to
    a suite that can only drive report() over hand-built fixtures. A review severed each of the two
    joins here in turn - the front-matter lookup and the touched-paths lookup - and the suite stayed
    green while the live map lost, respectively, every declared-placement attribution and every
    git-path attribution. Injecting the loader keeps this the one wiring point and makes the wiring
    itself drivable: the loader is asked for the four sibling paths BY NAME, so a stub can answer
    with known inputs and the composition below becomes observable rather than trusted.

    `root` IS HONOURED FOR EVERY INPUT OR IT WOULD BE WORSE THAN ABSENT. It used to reach the
    contract and the specs while the EVENT STREAM came from metrics.LOG, the GIT HISTORY from
    toe_corpus.ROOT and the PROTECTED PATTERNS from policy_check, all three resolved from wherever
    this file lives, so a map produced for repository X carried repository Y's cycles, spend and git
    attribution with nothing in the report saying so - the shape a caller cannot detect. The four
    siblings are now loaded FROM the tree under report, so each one's own root is that tree, and the
    map for X is derived by X's own organs over X's own data. A tree that does not carry them is
    refused BY NAME rather than reported over silently."""
    base = Path(root or ROOT)
    load = load if load is not None else (lambda name, rel: _load(name, rel, base))
    V = load("veldo_validate_ctc", ".veldo/validate.py")
    TC = load("veldo_toe_corpus_ctc", ".veldo/toe_corpus.py")
    M = load("veldo_metrics_ctc", ".veldo/metrics.py")
    PC = load("veldo_policy_check_ctc", ".veldo/policy_check.py")
    arch, contract = V.load_repo_contract(repo_root=str(base))
    corpus = TC.build(specs_dir=base / "specs", events=M.load(),
                      protected=PC.protected_patterns())
    fm = front_matter_index(base / "specs", V.parse_yamlish)
    return report(corpus, contract, arch, fm_of=fm.get,
                  paths_of=lambda s: TC.git_touched(s)["files"])


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="VELDO cost-to-change per architecture area, aggregated from the Tokens of "
                    "Effort actuals corpus. Advisory: nothing gates on these numbers.")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)
    try:
        rep = repo_report()
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    print(json.dumps(rep, indent=2, sort_keys=True) if args.json else render_text(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
