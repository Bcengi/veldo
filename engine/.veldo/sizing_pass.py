#!/usr/bin/env python3
"""The sizing pass: the optional second estimating layer (WARP-1403, W3 of PLAN-0014).

WHAT THIS IS. A small in-session agent reads a spec and the code that spec says it will
touch, predicts a RANGE with stated reasoning, and that prediction is recorded as ONE layer
of the estimate record WARP-1402 defined: `layer: sizing_pass`, `basis: agent_judgement`.
Three pieces, and only the middle one is an agent:

  THE BRIEF        deterministic, mechanical, no model call. Everything the agent is
                   allowed to look at, derived from the spec's own features, the code the
                   declared footprint resolves to, the measured state of the actuals
                   ledger, and the structural prior W2 already computed. Same tree, same
                   brief, same bytes, and its digest is what binds a judgement to it.
  THE JUDGEMENT    the agent's answer, a validated record in the front-matter subset:
                   a range, one line of reasoning, the model that produced it, and the
                   pass's OWN token cost. The agent writes it; this module only reads it.
  THE LAYER        the judgement turned into an estimate layer and handed to W2's
                   build seam, so the committed range is derived by the one combination
                   rule and nothing here assembles a record of its own.

***

THE SEAM FAILS LOUD AND NEVER FABRICATES. `LiveSizingAgent` is the reference agent and it
is wired to nothing: it RAISES. That is the same posture the executor's LiveLoop takes on
its build step and dispatch's LiveReviewer takes on its review, for the same reason - a
sizing pass that quietly returned a plausible range would be worse than none at all,
because the number would look measured and reconcile against a real actual later. Nothing
in this module computes a range from the brief. There is no fallback, no default and no
heuristic: the only paths that produce a judgement are an injected agent and a judgement
file an agent wrote, and both refuse rather than invent.

THE LAYER IS OPTIONAL AND ITS ABSENCE IS ORDINARY. A spec with no sizing pass is complete;
an estimate record carrying only the structural proxy is complete (PLAN-0014 C3, D3). With
no judgements present every reader here stands down silently and creates nothing. Nothing
in the gate calls this module, so no path through it can refuse, block or delay work on an
estimate (NG1). An estimate is not an acceptance criterion and never changes a spec's
validity.

AN AGENT'S JUDGEMENT NEVER MAKES AN ESTIMATE CALIBRATED. `agent_judgement` is deliberately
NOT one of W2's calibrated bases, so a record carrying this layer still reads
`calibration: uncalibrated`. This module checks that at the moment it writes a layer and
REFUSES if that ever stops being true, because the one thing a reasoned guess must never
do is arrive dressed as a measurement.

THE RANGE GETS WIDER OR STAYS PUT, NEVER NARROWER. The committed range is the ENVELOPE of
the layers present (W2), so adding this layer can only widen it. A sizing pass "sharpens"
by disagreeing visibly, not by tightening a band nothing supports; two layers that
disagree are evidence the answer is uncertain, which is NG6 in arithmetic.

***

THE MEASURED FINDING OF THIS ITEM, and it is why the honesty above is not decoration.

Measured over this repository's own log at the time of building: **1094 events, and NOT ONE
carries `tokens`, `cost_usd` or `human_minutes`. There is not a single `spec.shipped` spend
record in the ledger.** W1 measured the same gap at 904 events and shipped the emitter
(`spend.py`); nothing has called it since. So a sizing pass here has NO measured history to
anchor on, and the brief says exactly that: `anchor_available: no`, with the numeric anchor
fields OMITTED rather than reported as zero. A zero because nothing was spent and a zero
because nothing was ever recorded are different facts, and an agent handed the second as a
measurement would calibrate against nothing while feeling informed.

The consequence for this layer's own cost: recording it is, today, the FIRST spend record
this repository would ever write. That is recorded through `spend.py`'s writer, against the
spec being sized, exactly as any other work would be - so the estimating apparatus's cost
lands INSIDE the measured cost of the change it sized, where PLAN-0014 C4's
proportionality claim can be checked rather than asserted. The layer also carries the
share as `self_cost_bps_of_low` and a plain yes/no against a declared ceiling. It REPORTS
and never refuses: a pass that cost too much is a fact worth keeping, and deleting the
record of an expensive pass would hide the only evidence C4 is being violated.

***

THE JUDGEMENT SCHEMA: veldo.sizing_judgement/v1. One record per spec, one file per record,
at `.veldo/sizings/<SPEC-ID>.yaml`, read with the ONE parser (validate.parse_yamlish). The
filename is the key and the record's `spec` is checked against it rather than trusted, the
same discipline the estimate record keeps.

  schema            veldo.sizing_judgement/v1, exactly.
  spec              the spec id this judgement is about.
  brief_digest      the sha256 of the canonical brief the agent actually read, echoed back.
                    A judgement is only about the brief it was made from: if the spec, the
                    code it touches, the ledger or the structural prior has moved, the
                    digest no longer matches and the judgement is REFUSED rather than
                    silently applied to a different question. This is also what stops a
                    judgement being copied from one spec to another.
  model             the model identity that produced the judgement. Required, because this
                    layer's noise is a property of the model that made it and D5 windows
                    history by model identity; a prediction whose author is unknown cannot
                    be windowed, scored or trusted later.
  low, high         the predicted range, integers in the estimate record's unit, low
                    STRICTLY less than high. Checked by the SAME rule W2 holds its own
                    layers to (estimate._bounds_problems), fetched rather than respelled.
  reasoning         one line, at least MIN_REASONING_CHARS of it, and it becomes the
                    layer's note. A floor on saying something is mechanical; whether the
                    reasoning is GOOD is a reviewer's judgement and no gate's business. The
                    remaining spelling rules belong to the estimate record's renderer, which
                    refuses a value the ONE parser would not read back as itself, and they
                    are not respelled here: a reasoning it cannot spell is refused at write
                    time by that renderer, in its own words.
  self_cost_tokens  what this pass cost, a positive integer.
  self_cost_basis   how that number was arrived at, from spend.py's declared vocabulary
                    (its table, not a second one here).
  note              optional, one line.

WHAT THIS MODULE DOES NOT DO. It does not write a judgement: a module that could write one
could also invent one, so the judgement is the agent's own artifact and this side only
reads, validates and refuses. It does not match this spec against shipped specs in the
corpus - historical analogy is W4 and would be a different basis. It does not reconcile the
prediction against the actual, which is W5. And it does not read a clock: `at` is passed
in, so the same spec on the same date is the same bytes on any machine.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

SCHEMA = "veldo.sizing_judgement/v1"
BRIEF_SCHEMA = "veldo.sizing_brief/v1"
ROOT = Path(__file__).resolve().parent.parent
JUDGEMENTS_DIR = ".veldo/sizings"

# THE ONE LAYER THIS PASS WRITES, named from W2's declared vocabulary rather than invented
# here. `layer_vocabulary` checks both against that module's tables at use time, so a typo or
# a renamed vocabulary is a refusal instead of a contribution nothing recognises.
LAYER_ID = "sizing_pass"
LAYER_BASIS = "agent_judgement"

# A floor on STATING a reason, not a judgement of its quality. "big" is not reasoning; whether
# a paragraph is good reasoning is a reviewer's call and no gate can make it.
MIN_REASONING_CHARS = 40

# WHAT THIS PASS IS ALLOWED TO COST, in basis points of its own lower bound (500 = 5 percent),
# which is PLAN-0014 C4 written down. Crossing it is REPORTED in the layer and never refused:
# an expensive pass is a fact, and refusing to record it would delete the only evidence that
# the estimating apparatus is costing more than the work it sizes.
SELF_COST_CEILING_BPS = 500

RECORD_REQUIRED = ("schema", "spec", "brief_digest", "model", "low", "high", "reasoning",
                   "self_cost_tokens", "self_cost_basis")
RECORD_OPTIONAL = ("note",)

DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")

# Directories a brief never walks into: version control and bytecode are not the code a spec
# touches, and including them would make a brief's digest depend on whether anything had been
# imported recently.
WALK_SKIP_DIRS = ("__pycache__", ".git")

# WHAT THE AGENT IS ASKED FOR, carried IN the brief so the ask travels with the data rather
# than living in a prompt nobody can see afterwards. Every line here is also ENFORCED by
# `validate_judgement`: prose asks, code refuses, and the code is what makes it true.
ASK = (
    "Predict a RANGE in the estimate record's unit, never a single number.",
    "State one line of reasoning: what makes this change expensive or cheap.",
    "Echo brief_digest exactly, so the judgement is bound to the brief you actually read.",
    "Name the model you are, because this layer's accuracy is a property of that model.",
    "Report your OWN token cost for this pass, and say how you arrived at the number.",
    "You have no measured history to anchor on unless the ledger below says otherwise; "
    "say wide rather than confident.",
)

_MODS = {}


class SizingPassError(Exception):
    """Every refusal this module makes. One type, so a caller can tell a refusal from a bug."""


def _mod(rel, name):
    """One of this engine's modules, loaded from THIS engine's location, cached. The same
    importlib shape estimate.py and spend.py use, for the same reason: reuse the one
    implementation rather than spelling it again."""
    if name not in _MODS:
        spec = importlib.util.spec_from_file_location(name, ROOT / rel)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MODS[name] = mod
    return _MODS[name]


def _validate():
    """The ONE parser and the ONE failure reporter (.veldo/validate.py)."""
    return _mod(".veldo/validate.py", "veldo_validate_sizing")


def _estimate():
    """The estimate record, the layer vocabulary and the structural prior (W2)."""
    return _mod(".veldo/estimate.py", "veldo_estimate_sizing")


def _corpus():
    """The ONE spec-feature reader, the ONE footprint reader and the declared spend field
    names (W1). The brief reads features THROUGH this so the features an agent was shown are
    the features the actuals corpus later records against the same spec."""
    return _mod(".veldo/toe_corpus.py", "veldo_toe_corpus_sizing")


def _arch():
    """The ONE glob compiler (arch._glob_re), so what a footprint glob matches here is what it
    matches for the shape gate and for area resolution. A second glob implementation would be
    a second answer to one question."""
    return _mod(".veldo/arch.py", "veldo_arch_sizing")


def _spend():
    """The ONE spend writer and its declared provenance vocabulary (W1b)."""
    return _mod(".veldo/spend.py", "veldo_spend_sizing")


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def layer_vocabulary():
    """(layer id, basis) for this pass, CHECKED against W2's declared tables. Fails closed by
    name on three things, and the third is the load-bearing one:

      - a layer id W2 does not declare (a typo would otherwise be an unrecognised layer),
      - a basis W2 does not declare (a number with no stated provenance is over-trusted),
      - a basis W2 counts as GROUNDED IN RECORDED ACTUALS. An agent's prediction is not a
        measurement, and if `agent_judgement` were ever moved into that set, every record
        carrying this layer would start reading `calibration: calibrated` off a guess. This
        module refuses to write the layer at all in that case rather than let it happen."""
    E = _estimate()
    if LAYER_ID not in E.LAYERS:
        raise SizingPassError("layer id %r is not one of the layers veldo.estimate/v1 declares "
                              "(%s): the sizing pass extends that vocabulary, it does not widen "
                              "it" % (LAYER_ID, sorted(E.LAYERS)))
    if LAYER_BASIS not in E.BASES:
        raise SizingPassError("basis %r is not one of the bases veldo.estimate/v1 declares (%s)"
                              % (LAYER_BASIS, sorted(E.BASES)))
    if LAYER_BASIS in E.CALIBRATED_BASES:
        raise SizingPassError(
            "basis %r is declared as grounded in recorded actuals (%s), and an agent's "
            "prediction is not: refusing to write a layer that would make an estimate read "
            "calibrated off a judgement nobody measured"
            % (LAYER_BASIS, list(E.CALIBRATED_BASES)))
    return LAYER_ID, LAYER_BASIS


def _bounds_rule():
    """The ONE bounds rule: the same integers-positive-and-strictly-ordered check W2 holds its
    own layers to, fetched from that module rather than respelled here. A refusal if it is
    gone, because two spellings of the point-estimate refusal is exactly how one of them later
    starts accepting a point."""
    E = _estimate()
    fn = getattr(E, "_bounds_problems", None)
    if not callable(fn):
        raise SizingPassError("the bounds rule of veldo.estimate/v1 is unavailable in %s: "
                              "refusing to re-spell the point-estimate refusal here"
                              % getattr(E, "__file__", "the estimate module"))
    return fn


# ---------------------------------------------------------------------------------------
# The brief: mechanical, deterministic, and the only thing the agent is shown.
# ---------------------------------------------------------------------------------------

def _refuse_escape(entry, where):
    """A footprint entry that leaves the repository is refused BEFORE anything is read. A
    brief that could read outside the tree is a brief that could be pointed at a secret."""
    if not isinstance(entry, str) or not entry.strip():
        raise SizingPassError("%s: a footprint entry must be a non-empty path glob, got %r"
                              % (where, entry))
    e = entry.strip()
    if e.startswith("/") or e.startswith("~"):
        raise SizingPassError("%s: refusing the absolute footprint entry %r: a brief reads only "
                              "inside the repository" % (where, entry))
    if ".." in e.split("/"):
        raise SizingPassError("%s: refusing the footprint entry %r: it escapes the repository "
                              "root, and a brief reads only inside it" % (where, entry))
    return e


def _file_facts(base, rel):
    """(bytes, lines) for one repo-relative file. `lines` counts newlines plus a final
    unterminated line, which is the count a reader expects."""
    data = (Path(base) / rel).read_bytes()
    if not data:
        return 0, 0
    return len(data), data.count(b"\n") + (0 if data.endswith(b"\n") else 1)


def _walk(base, start):
    """Every file under one subtree, repo-relative and sorted, skipping version control and
    bytecode. Deterministic for a given tree, which is what lets a brief have a digest."""
    out = []
    top = Path(base) / start if start else Path(base)
    if not top.is_dir():
        return out
    for dirpath, dirnames, filenames in os.walk(top):
        dirnames[:] = sorted(d for d in dirnames if d not in WALK_SKIP_DIRS)
        for fn in sorted(filenames):
            if fn.endswith(".pyc"):
                continue
            out.append(str((Path(dirpath) / fn).relative_to(base)))
    return sorted(out)


def _literal_prefix(pattern):
    """The deepest directory of a pattern before its first metacharacter, so resolving a glob
    walks the smallest subtree that could contain a match instead of the whole repository."""
    cuts = [i for i, c in enumerate(pattern) if c in "*?["]
    head = pattern[:min(cuts)] if cuts else pattern
    return head.rsplit("/", 1)[0] if "/" in head else ""


def code_facts(footprint, root=None):
    """WHAT CODE THIS CHANGE WILL TOUCH, resolved from the spec's declared footprint.

    One entry per declared glob, each saying which of four things it is, because they are four
    different sizing problems and a single count would blur them:

      file       a literal path that exists: bytes and lines, the code to be READ and changed.
      absent     a literal path that does not exist: a file to be CREATED. Greenfield work
                 sizes differently from editing a large module, and the corpus has 26 such
                 entries against 638 existing ones, so this is not a corner case.
      directory  a literal directory: resolved by walking it.
      pattern    a glob, resolved through the ONE glob compiler (arch._glob_re) over the
                 smallest subtree that can match. 121 of this repository's 785 footprint
                 entries carry a metacharacter, so refusing to resolve them would blind the
                 brief on one entry in six.

    `bytes` and `lines` are present only where something was actually measured: an entry that
    matched nothing carries no size at all rather than a zero that reads like a measurement."""
    base = Path(root) if root else ROOT
    rx = _arch()._glob_re
    entries, existing, to_create, patterns, unmatched = [], 0, 0, 0, 0
    tot_bytes = tot_lines = 0
    for raw in footprint or ():
        e = _refuse_escape(raw, "footprint")
        p = base / e
        if any(c in e for c in "*?["):
            patterns += 1
            m = rx(e)
            paths = [f for f in _walk(base, _literal_prefix(e)) if m.match(f)]
            kind = "pattern"
            if not paths:
                # A GLOB THAT MATCHED NOTHING IS ITS OWN FACT, counted separately from a
                # literal path that is absent. The literal one is a file to be created; this
                # one is ambiguous (files to create, or a glob that has gone stale), and
                # folding it into either count would state something nobody measured.
                unmatched += 1
        elif p.is_file():
            paths, kind = [e], "file"
        elif p.is_dir():
            paths, kind = _walk(base, e), "directory"
        else:
            to_create += 1
            entries.append({"entry": e, "kind": "absent", "matched": 0, "paths": []})
            continue
        ent = {"entry": e, "kind": kind, "matched": len(paths), "paths": paths}
        if paths:
            b = l = 0
            for f in paths:
                fb, fl = _file_facts(base, f)
                b += fb
                l += fl
            ent["bytes"], ent["lines"] = b, l
            tot_bytes += b
            tot_lines += l
            existing += len(paths)
        entries.append(ent)
    return {"declared": len(list(footprint or ())), "entries": entries,
            "existing_files": existing, "to_create": to_create, "patterns": patterns,
            "patterns_unmatched": unmatched,
            "existing_bytes": tot_bytes, "existing_lines": tot_lines}


def ledger_state(events):
    """WHAT MEASURED HISTORY EXISTS FOR THE AGENT TO ANCHOR ON, and emptiness reported as
    emptiness.

    The numeric fields are OMITTED when nothing is recorded rather than reported as zero. That
    is the whole point of this block: measured over this repository, 1094 events carry no spend
    field at all, and an agent handed `tokens_recorded: 0` would read a measurement where there
    is none. `anchor_available: no` is the honest answer and the ask above tells the agent what
    to do with it.

    It is a PRESENCE report and never an analogy: matching this spec to similar shipped specs
    and predicting from their actuals is W4, on a different basis. Reuses W1's declared spend
    field names, so the two cannot disagree about what recorded spend means."""
    E = _estimate()
    fields = _corpus().SPEND_FIELDS
    evs = [e for e in (events or ()) if isinstance(e, dict)]
    carrying = [e for e in evs if any(_is_num(e.get(k)) for k in fields)]
    out = {"events": len(evs), "spend_events": len(carrying),
           "anchor_available": E.YES if carrying else E.NO}
    if carrying:
        out["tokens_recorded"] = sum(int(e["tokens"]) for e in carrying
                                     if _is_num(e.get("tokens")))
        out["specs_with_spend"] = len({e.get("spec_id") or e.get("correlation_id")
                                       for e in carrying
                                       if e.get("spec_id") or e.get("correlation_id")})
    return out


def brief(spec_path, protected=(), events=(), root=None):
    """THE BRIEF the sizing agent reads: the spec's mechanical features, the code its declared
    footprint resolves to, the state of the actuals ledger, the structural prior W2 already
    computed, and the ask.

    Deterministic and mechanical: no clock, no network, no subprocess, no model call. The
    caller owns the event list and the protected set exactly as toe_corpus.build does, so a
    test drives this with seeded inputs and it never reaches for the real log behind a
    caller's back.

    THE PRIOR IS SHOWN ON PURPOSE. An agent that cannot see what the mechanical layer already
    said is being asked to re-derive it, and its judgement adds nothing. Because the prior is
    part of the brief it is part of the DIGEST, so refitting the structural model (W5) changes
    the digest and retires every judgement made against the old one - which is correct: that
    judgement was made from different information."""
    E = _estimate()
    C = _corpus()
    f = C.spec_features(spec_path)
    if not f.get("spec_id"):
        raise SizingPassError("refusing to brief %s: it declares no spec id, so no judgement "
                              "could be filed against it" % spec_path)
    fp = C.footprint_of(Path(spec_path).read_text())
    prior = E.structural_proxy(spec_path, protected, root)
    return {
        "schema": BRIEF_SCHEMA,
        "spec": f["spec_id"],
        "features": {k: f.get(k) for k in ("status", "risk", "plan", "lane",
                                           "acceptance_criteria", "footprint_declared",
                                           "depends_on", "spec_bytes")},
        "protected_touch": E.YES if C.protected_touch(fp, tuple(protected)) else E.NO,
        "code": code_facts(fp, root),
        "ledger": ledger_state(events),
        "prior": {"layer": prior["layer"], "basis": prior["basis"],
                  "low": prior["low"], "high": prior["high"],
                  "expected_review_cycles": prior["inputs"]["expected_review_cycles"]},
        "unit": _brief_unit(E),
        "asked_of_the_agent": list(ASK),
    }


def _brief_unit(E):
    """The unit both bounds must be in, taken from W2's declared vocabulary rather than spelled
    again here. v1 declares exactly one; if that ever becomes several, a brief cannot tell an
    agent which one to answer in, so it REFUSES rather than choosing on the agent's behalf."""
    units = sorted(E.UNITS)
    if len(units) != 1:
        raise SizingPassError("veldo.estimate/v1 declares %d units (%s): a brief cannot tell an "
                              "agent which one to predict in, so it refuses rather than "
                              "choosing for it" % (len(units), units))
    return units[0]


def canonical_brief(b):
    """The brief's canonical bytes: one serialization, sorted and tight, so the digest is a
    property of the brief's CONTENT and not of how anybody printed it."""
    return json.dumps(b, sort_keys=True, separators=(",", ":")).encode("utf-8")


def brief_digest(b):
    """The sha256 a judgement echoes back. This is the whole binding: a judgement is about the
    brief it was made from, and any movement in the spec, the code, the ledger or the prior
    changes this digest and retires the judgement instead of silently reusing it."""
    return hashlib.sha256(canonical_brief(b)).hexdigest()


def render_brief(b):
    """The brief as the agent receives it: the brief and its digest together, so the agent has
    the digest it must echo without computing anything."""
    return json.dumps({"brief": b, "brief_digest": brief_digest(b)},
                      sort_keys=True, indent=1) + "\n"


# ---------------------------------------------------------------------------------------
# The judgement: validation and reading. This module never WRITES one.
# ---------------------------------------------------------------------------------------

def validate_judgement(rec, brief_rec=None):
    """Every problem with one judgement, as strings that NAME what is wrong. Empty means the
    judgement is usable. Fail closed: an unknown key, an unknown provenance and a range that
    is not a range are refusals, never silently-ignored input.

    `brief_rec`, when given, is the brief the judgement claims to be about, and the two are
    checked against each other rather than one being trusted."""
    out = []
    if not isinstance(rec, dict):
        return ["a sizing judgement must be a mapping, got %s" % type(rec).__name__]
    unknown = sorted(set(rec) - set(RECORD_REQUIRED) - set(RECORD_OPTIONAL))
    if unknown:
        out.append("unknown key(s) %s: veldo.sizing_judgement/v1 declares %s (required) and %s "
                   "(optional), and an unknown key is refused rather than ignored"
                   % (unknown, list(RECORD_REQUIRED), list(RECORD_OPTIONAL)))
    for k in RECORD_REQUIRED:
        if k not in rec:
            out.append("missing required key %r" % k)
    if "schema" in rec and rec["schema"] != SCHEMA:
        out.append("schema must be %r, got %r" % (SCHEMA, rec.get("schema")))
    if "spec" in rec and not (isinstance(rec["spec"], str) and rec["spec"].strip()):
        out.append("spec must name the spec this judgement is about, got %r" % (rec.get("spec"),))
    if "brief_digest" in rec and not (isinstance(rec["brief_digest"], str)
                                      and DIGEST_RE.match(rec["brief_digest"])):
        out.append("brief_digest must be a 64-character lowercase sha256 of the brief that was "
                   "read, got %r" % (rec.get("brief_digest"),))
    for key, minimum in (("model", 1), ("reasoning", MIN_REASONING_CHARS), ("note", 1)):
        if key in rec:
            out.extend(_line_problems(rec.get(key), key, minimum))
    out.extend(_bounds_rule()(rec, "the sizing pass's predicted range"))
    if "self_cost_tokens" in rec and not (_is_int(rec["self_cost_tokens"])
                                          and rec["self_cost_tokens"] > 0):
        out.append("self_cost_tokens must be a positive integer: this pass costs something, and "
                   "a pass that reports nothing is the silence the spend emitter exists to "
                   "replace, got %r" % (rec.get("self_cost_tokens"),))
    bases = _spend().BASES
    if "self_cost_basis" in rec and rec["self_cost_basis"] not in bases:
        out.append("self_cost_basis must be one of %s (the spend recorder's own declared "
                   "vocabulary, not a second table here), got %r"
                   % (sorted(bases), rec.get("self_cost_basis")))
    if brief_rec is not None:
        out.extend(_binding_problems(rec, brief_rec))
    return out


def _line_problems(value, where, minimum):
    """One single-line string field. The one-line rule is not style: the reasoning becomes the
    layer's note, and the estimate record's renderer refuses a multi-line value because the
    front-matter parser would not read it back as itself."""
    if not isinstance(value, str) or not value.strip():
        return ["%s must be a non-empty single-line string, got %r" % (where, value)]
    if "\n" in value or "\t" in value:
        return ["%s must be ONE line: it is written into the estimate record, whose renderer "
                "refuses a multi-line value because the parser would not read it back as "
                "itself" % where]
    if len(value.strip()) < minimum:
        return ["%s is %d characters and at least %d are required: a floor on SAYING something "
                "is mechanical, while whether the reasoning is good is a reviewer's judgement "
                "and no gate's business" % (where, len(value.strip()), minimum)]
    return []


def _binding_problems(rec, brief_rec):
    """The judgement against the brief it claims to be about. Two checks, both refusals:
    the spec must be the same spec, and the digest must be the same digest."""
    out = []
    if not isinstance(brief_rec, dict) or brief_rec.get("schema") != BRIEF_SCHEMA:
        return ["cannot bind this judgement: %r is not a %s brief"
                % (type(brief_rec).__name__, BRIEF_SCHEMA)]
    if rec.get("spec") != brief_rec.get("spec"):
        out.append("this judgement says spec %r but the brief is for %r: a judgement is about "
                   "the spec it was briefed on and cannot be moved to another"
                   % (rec.get("spec"), brief_rec.get("spec")))
    want = brief_digest(brief_rec)
    if rec.get("brief_digest") != want:
        out.append("brief_digest %r does not match the brief actually read (%r): the spec, the "
                   "code it touches, the ledger or the structural prior has moved since this "
                   "judgement was made, so it is about a different question and is refused "
                   "rather than reused" % (rec.get("brief_digest"), want))
    return out


def parse_judgement(text):
    """One judgement's text through the ONE parser. A parse failure is a refusal that carries
    the parser's own hint, never a silently empty record."""
    try:
        rec = _validate().parse_yamlish(text)
    except ValueError as e:
        raise SizingPassError("sizing judgement is outside the front-matter parser subset: %s"
                              % e)
    if not isinstance(rec, dict):
        raise SizingPassError("a sizing judgement must be a mapping, got %s"
                              % type(rec).__name__)
    return rec


def read_judgement(path, spec_id=None, brief_rec=None):
    """One judgement from disk, fail closed. The filename is the key, so a record filed under
    the wrong name is refused rather than trusted."""
    p = Path(path)
    if spec_id is None:
        spec_id = p.stem
    rec = parse_judgement(p.read_text())
    problems = validate_judgement(rec, brief_rec)
    if rec.get("spec") != spec_id:
        problems.append("this judgement is filed as %r but says spec: %r; the filename is the "
                        "key" % (spec_id, rec.get("spec")))
    if problems:
        raise SizingPassError("refusing the sizing judgement at %s: %s"
                              % (p, "; ".join(problems)))
    return rec


def judgements_dir(root=None):
    return (Path(root) if root else ROOT) / JUDGEMENTS_DIR


def judgement_for(spec_id, dirpath=None, root=None):
    """The judgement for one spec, or None. None is an ORDINARY answer: the sizing pass is
    optional and its absence invalidates nothing."""
    d = Path(dirpath) if dirpath else judgements_dir(root)
    p = d / ("%s.yaml" % spec_id)
    if not p.is_file():
        return None
    return read_judgement(p, spec_id=spec_id)


def load_dir(dirpath=None, root=None):
    """Every valid judgement present, keyed by spec id, plus the problems found.

    ADOPTION SAFE: an absent directory is not an error, it is a repository that does not use
    this, and it yields ({}, []) without creating anything. FAIL CLOSED: a judgement that is
    present and malformed is reported BY NAME rather than quietly dropped from the set."""
    d = Path(dirpath) if dirpath else judgements_dir(root)
    if not d.is_dir():
        return {}, []
    out, problems = {}, []
    for p in sorted(d.glob("*.yaml")):
        try:
            rec = read_judgement(p)
        except (SizingPassError, OSError) as e:
            problems.append(str(e))
            continue
        if rec["spec"] in out:
            problems.append("two judgements claim spec %r: %s" % (rec["spec"], p))
            continue
        out[rec["spec"]] = rec
    return out, problems


def layer_of(record):
    """The sizing_pass layer of an estimate record, or None. None is ordinary: a record with
    only a structural proxy is complete."""
    for l in (record or {}).get("layers") or ():
        if isinstance(l, dict) and l.get("layer") == LAYER_ID:
            return l
    return None


# ---------------------------------------------------------------------------------------
# The layer, and the pass that produces it.
# ---------------------------------------------------------------------------------------

class SizingAgent:
    """THE SEAM. size(brief) returns a judgement mapping in veldo.sizing_judgement/v1 shape.

    A concrete agent reads the brief in session, reasons about the spec and the code the brief
    resolved, and returns its own prediction. This module talks only to this interface, so the
    mechanical half is testable with a fake and the reference cannot fabricate a judgement."""

    def size(self, brief):
        raise NotImplementedError


class LiveSizingAgent(SizingAgent):
    """Reference agent wired to nothing. FAILS LOUD, exactly as the executor's LiveLoop refuses
    to fabricate a build and dispatch's LiveReviewer refuses to fabricate a verdict.

    There is no default range and no heuristic anywhere in this module. A sizing pass that
    invented a plausible number would be worse than no sizing pass at all: the number would be
    indistinguishable from a real prediction, it would widen a committed range on nothing, and
    W5 would later reconcile a real actual against a fabrication."""

    def size(self, brief):
        raise SizingPassError(
            "the sizing pass is a delegated in-session agent step and no agent is wired: "
            "inject an agent that reads the brief and returns its own judgement, or pass the "
            "judgement it wrote through JudgementFileAgent. Refusing to fabricate a "
            "judgement.")


class JudgementFileAgent(SizingAgent):
    """TRANSPORT, NOT AN ESTIMATOR. It carries a judgement an in-session agent already wrote
    to a file; it cannot produce one. An absent file and a malformed file are both refusals,
    so the only way a judgement exists here is that an agent made it."""

    def __init__(self, path):
        self.path = Path(path)

    def size(self, brief):
        if not self.path.is_file():
            raise SizingPassError("no sizing judgement at %s: this carries an agent's judgement, "
                                  "it does not make one. Refusing to fabricate a judgement."
                                  % self.path)
        return parse_judgement(self.path.read_text())


def layer_from(judgement, brief_rec=None):
    """ONE layer contribution: the agent's judgement as the estimate record's sizing_pass
    layer. Refuses an invalid judgement rather than clamping it into shape.

    The layer records the judgement's OWN cost and what share of its own lower bound that is,
    which is PLAN-0014 C4 made checkable, plus the digest of the brief it was made from and
    the model that made it (D5). Crossing the ceiling is reported, never refused."""
    problems = validate_judgement(judgement, brief_rec)
    if problems:
        raise SizingPassError("refusing to build a sizing_pass layer: " + "; ".join(problems))
    lid, basis = layer_vocabulary()
    E = _estimate()
    low, high = judgement["low"], judgement["high"]
    cost = judgement["self_cost_tokens"]
    bps = cost * 10000 // low
    inputs = {
        "brief_digest": judgement["brief_digest"],
        "model": judgement["model"],
        "self_cost_tokens": cost,
        "self_cost_basis": judgement["self_cost_basis"],
        "self_cost_bps_of_low": bps,
        "self_cost_ceiling_bps": SELF_COST_CEILING_BPS,
        "self_cost_within_ceiling": E.YES if bps <= SELF_COST_CEILING_BPS else E.NO,
    }
    if brief_rec is not None:
        inputs.update({
            "brief_acceptance_criteria": brief_rec["features"]["acceptance_criteria"],
            "brief_regression_surface": brief_rec["features"]["footprint_declared"],
            "brief_existing_files": brief_rec["code"]["existing_files"],
            "brief_files_to_create": brief_rec["code"]["to_create"],
            "brief_existing_lines": brief_rec["code"]["existing_lines"],
            "brief_prior_low": brief_rec["prior"]["low"],
            "brief_prior_high": brief_rec["prior"]["high"],
            "brief_ledger_spend_events": brief_rec["ledger"]["spend_events"],
        })
    return {"layer": lid, "basis": basis, "low": low, "high": high,
            "note": judgement["reasoning"].strip(), "inputs": inputs}


def assert_prior_agrees(record, brief_rec):
    """ONE ENUMERATION OF THE PRIOR, asserted rather than assumed.

    The brief shows the agent the structural layer's range, and the committed record derives
    that layer again from the same spec. Two derivations of one number diverge the moment
    anything between them differs, so this REFUSES when they disagree instead of committing a
    record whose prior is not the prior the judgement was made against."""
    layers = [l for l in (record or {}).get("layers") or ()
              if isinstance(l, dict) and l.get("layer") == brief_rec["prior"]["layer"]]
    if len(layers) != 1:
        raise SizingPassError("the record carries %d %r layer(s): a sizing pass composes with "
                              "exactly one structural prior"
                              % (len(layers), brief_rec["prior"]["layer"]))
    got = (layers[0].get("low"), layers[0].get("high"))
    want = (brief_rec["prior"]["low"], brief_rec["prior"]["high"])
    if got != want:
        raise SizingPassError("the brief showed a structural prior of %r but the committed "
                              "record derives %r: a judgement made against a prior that is not "
                              "the one committed is a judgement about a different question"
                              % (want, got))
    return True


def size(spec_path, at, agent=None, protected=(), events=(), root=None):
    """THE WHOLE PASS: brief, ask, validate, compose. Returns the brief, its digest, the
    judgement, the layer and the committed estimate record.

    The agent call is NOT wrapped in a handler. A raising agent raises out of here, because the
    alternative is a fallback, and a fallback here is a fabricated estimate.

    The record is assembled by W2's own build seam (estimate.propose with an extra layer), so
    the committed range is derived by the one declared combination rule and this module never
    computes a committed range of its own. Adding this layer can only WIDEN that range."""
    b = brief(spec_path, protected, events, root)
    judgement = (agent or LiveSizingAgent()).size(b)
    layer = layer_from(judgement, b)
    rec = _estimate().propose(spec_path, at, protected=protected, root=root,
                              extra_layers=[layer])
    assert_prior_agrees(rec, b)
    return {"brief": b, "brief_digest": brief_digest(b), "judgement": judgement,
            "layer": layer, "record": rec}


def record_self_cost(judgement, emit=None):
    """The pass's OWN token cost, appended through the ONE spend writer (spend.record), against
    the spec it sized.

    Recorded like any other work, deliberately: the estimating apparatus's cost lands inside
    the measured cost of the change it sized, which is the only way C4's proportionality claim
    can be checked instead of asserted. `emit` is injectable so a test drives this without
    touching the real log, exactly as spend.py intends."""
    problems = validate_judgement(judgement)
    if problems:
        raise SizingPassError("refusing to record the sizing pass's own cost: "
                              + "; ".join(problems))
    return _spend().record(
        judgement["spec"], judgement["self_cost_basis"],
        tokens=judgement["self_cost_tokens"],
        note="sizing pass for %s by %s, brief %s"
             % (judgement["spec"], judgement["model"], judgement["brief_digest"][:12]),
        emit=emit)


# ---------------------------------------------------------------------------------------
# Reporting. Uses validate.fail, the ONE failure reporter.
# ---------------------------------------------------------------------------------------

def check_dir(dirpath=None, root=None):
    """Validate every committed judgement. Returns (count, errs).

    Adoption safe and SILENT about it: with no directory there is nothing to say. This is a
    REPORT and never a gate stage - nothing in scripts/verify.sh calls it, because a spec's
    validity may not depend on an optional estimate (C3, NG1)."""
    V = _validate()
    d = Path(dirpath) if dirpath else judgements_dir(root)
    if not d.is_dir():
        return 0, 0
    n = errs = 0
    for p in sorted(d.glob("*.yaml")):
        n += 1
        try:
            rec = parse_judgement(p.read_text())
        except (SizingPassError, OSError) as e:
            errs += V.fail(str(p), str(e))
            continue
        problems = validate_judgement(rec)
        if rec.get("spec") != p.stem:
            problems.append("filed as %r but says spec: %r; the filename is the key"
                            % (p.stem, rec.get("spec")))
        for problem in problems:
            errs += V.fail(str(p), problem)
    return n, errs


def _read_events(path=None, root=None):
    """The event log through the event module's ONE reader, so the ledger report and every
    other reader agree about what an event is."""
    base = Path(root) if root else ROOT
    p = Path(path) if path else base / ".veldo" / "events.jsonl"
    return _mod(".veldo/events.py", "veldo_events_sizing").read_log(p)


def _cli(argv):
    ap = argparse.ArgumentParser(
        prog="sizing_pass.py",
        description="The optional second estimating layer: an in-session agent reads a brief "
                    "and predicts a range, recorded as one layer of the spec's estimate. "
                    "Advisory only: nothing here gates, blocks or delays any work.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    br = sub.add_parser("brief", help="the deterministic brief for one spec, for an agent to read")
    br.add_argument("--spec", required=True)
    sz = sub.add_parser("size", help="compose an agent's judgement into the spec's estimate")
    sz.add_argument("--spec", required=True)
    sz.add_argument("--at", required=True,
                    help="the date the estimate is committed, YYYY-MM-DD. Never read from a "
                         "clock, so the same spec on the same date is the same bytes")
    sz.add_argument("--judgement", help="path to the judgement the in-session agent wrote. "
                                        "Without it there is no agent wired and this refuses "
                                        "rather than inventing a range")
    sz.add_argument("--write", action="store_true", help="commit the estimate record")
    sz.add_argument("--replace", action="store_true", help="overwrite a committed estimate")
    sz.add_argument("--record-cost", action="store_true",
                    help="append the pass's own token cost to the event log")
    ck = sub.add_parser("check", help="validate every committed judgement")
    ck.add_argument("--dir")
    sub.add_parser("vocab", help="the layer, the basis, the cost vocabulary and the ask")
    a = ap.parse_args(argv)

    if a.cmd == "vocab":
        return _cli_vocab()
    if a.cmd == "check":
        d = Path(a.dir) if a.dir else judgements_dir()
        n, errs = check_dir(d)
        if n == 0:
            print("sizing judgements: none under %s - standing down (this is not a finding)" % d)
            return 0
        print("sizing judgements: %d record(s) checked, %d problem(s)" % (n, errs))
        return 1 if errs else 0
    E = _estimate()
    try:
        if a.cmd == "brief":
            print(render_brief(brief(a.spec, protected=E.protected_paths(),
                                     events=_read_events())), end="")
            return 0
        agent = JudgementFileAgent(a.judgement) if a.judgement else LiveSizingAgent()
        out = size(a.spec, a.at, agent=agent, protected=E.protected_paths(),
                   events=_read_events())
        if a.write:
            print("wrote %s" % E.write_record(out["record"], replace=a.replace))
        if a.record_cost:
            print("recorded %s" % json.dumps(record_self_cost(out["judgement"]),
                                             sort_keys=True))
        print(E.render_record(out["record"]), end="")
        return 0
    except (SizingPassError, ValueError, OSError) as e:
        print(str(e), file=sys.stderr)
        return 1


def _cli_vocab():
    E = _estimate()
    print("layer:   %-16s %s" % (LAYER_ID, E.LAYERS[LAYER_ID][1]))
    print("basis:   %-16s %s" % (LAYER_BASIS, E.BASES[LAYER_BASIS]))
    print("calibration: an agent's judgement is NOT grounded in recorded actuals, so a record "
          "carrying this layer stays uncalibrated")
    print("self-cost provenance (from the spend recorder's own table):")
    for k, v in sorted(_spend().BASES.items()):
        print("  %-18s %s" % (k, v))
    print("self-cost ceiling: %d basis points of the layer's own low (reported, never "
          "enforced)" % SELF_COST_CEILING_BPS)
    print("asked of the agent:")
    for line in ASK:
        print("  - %s" % line)
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
