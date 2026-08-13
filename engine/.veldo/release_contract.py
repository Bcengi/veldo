#!/usr/bin/env python3
"""VELDO release contract and registry (veldo.release/v1): the unit ABOVE the plan, and the
one place a group of plans is typed.

THE CAPABILITY, in the founder's words: "MVP is very specific for first release but maybe
Release is more appropriate. Among them is MVP release or any other. But it is actually
needed. How would you scope a release? With a single plan? No, it needs to be group of plans
(plan of plans)." So the unit above the plan is the release, an MVP is simply the first one,
and this module builds the BOTTOM of that layer: the artifact, its registry, the type rule
that makes the plan the floor, the graph rules that make the member set a forest, and the
content binding every later receipt rests on. It builds NOTHING above that: no ordering, no
two-way binding, no derived view, no receipt, no command. A verb the code does not have is
not documented here.

THE NAME, so no reader has to guess. `.veldo/release.py` is a DIFFERENT organ and is not
renamed: it owns staged rollout and rollback EXECUTION. This module, `.veldo/release_contract.py`,
owns the release ARTIFACT and its registry, and its name says which of the two it is rather than
leaning on a plural somebody has to notice. Nothing here calls that module and nothing there
calls this one. The artifacts themselves live flat in `releases/`, like plans.

DEPENDENCY FREE BY CONSTRUCTION, in the shape .veldo/request.py and .veldo/decision.py
already use: the caller (.veldo/validate.py) hands in the ONE front-matter parser
(validate.parse_yamlish) and the ONE failure reporter (validate.fail). This module therefore
adds NO second YAML parser, and there is no import cycle: validate.py may load this, and this
loads nothing of validate.py.

TWO SHIPPED DEFECTS ARE FIXED HERE, both verified in the code rather than theorised:

  A MEMBER IS BOUND BY THE BYTES OF ITS FILE. `plan.plan_hash` (.veldo/plan.py:216-222)
  hashes the parsed FRONT MATTER with approved_at and recorded_at dropped and truncates to 16
  hex, so a member plan's entire body can be rewritten after a binding is written and the
  binding still matches: a hole exactly the size of a plan body. `member_digest` below reads
  the file BYTES the way .veldo/request_reconcile.py:131-139 reads them and keeps ALL 64 hex
  characters, the width this repository already uses where a digest BINDS a decision rather
  than labelling an artifact for a human to eyeball, whose validator likewise requires the
  full width. `plan_hash` is
  deliberately NOT changed: it serves a proof binding that is right to ignore when a plan was
  approved, and a shipped assertion pins that behaviour
  (scripts/suites/01_warp_0101_reviewer_notes.py:471).

  NO TWO ARTIFACTS SHARE AN ID, IN EITHER REGISTRY, THROUGH ONE SPELLING OF THE RULE.
  `validate.plan_registry` (.veldo/validate.py:652-670) writes `reg[fm["id"]] = ...` once per
  file with no duplicate check, so two plan files declaring one id leave the validator
  reporting zero errors while one file disappears from every derived view. `duplicate_ids`
  below is the ONE rule, taking an id-to-paths mapping so the release registry and the plan
  registry cannot grow two copies of it, and `id_paths` is the ONE mapping producer both feed
  it. The registry's return shape does not move and it still does not raise: the duplicates
  are exposed through a separate accessor and refused at the corpus check, because eight
  callers read that registry (.veldo/plan.py:49, .veldo/budget.py:288, .veldo/toe_budget.py:904,
  .veldo/runstatus.py:136, .veldo/judgment_load.py:581, .veldo/intent_corpus.py:552,
  scripts/update_index.py:48, and the suites) and a reader that began raising would redden the
  gate far from the defect.

TWO POSTURES, both shared with the organs this mirrors.

  ADOPTION SAFE. Two conditions stand the release check down, and both produce the SAME
  report shape a live read produces, each naming which condition it was: no releases
  directory at all, and a releases directory declaring no release (the template is excluded
  exactly as plan_registry excludes it, .veldo/validate.py:658-659). The stand-down is NEVER
  keyed on the directory, because shipping the template CREATES the directory and a
  directory-keyed stand-down would silently stop standing down the moment the template
  landed. It is keyed on the CANDIDATE FILE SET rather than on the resolved registry, which
  the suite found by driving it: a release file declaring no id leaves the registry empty
  while the corpus plainly holds a release, and a registry-keyed stand-down let that broken
  file pass as an unadopted repository.
  `check_plan_ids` does NOT stand down with it: a duplicate plan id is a defect in the plan
  corpus whether or not any release exists, which is why the two are registered separately.

  FAIL CLOSED. A malformed record, a missing required field, an out-of-vocabulary status or
  kind, an unknown member kind, a member target whose id shape belongs to another artifact
  type, a member cycle, a member claimed by two releases, a duplicate id in either registry,
  and two releases both claiming to be the MVP each refuse BY NAME. One refusal surface with
  named causes, all read from ONE problem enumeration (`release_problems`) that both the
  reporting form (`release_report`) and the refusing form (`check_release`) consume, so the
  two surfaces cannot disagree about what is wrong.

WHAT IS REPORTED RATHER THAN REFUSED, and why that is not a softening. MEASURED on
2026-08-11: seventeen of this repository's eighteen plan files declare `kind: mvp` (the
exception is plans/PLAN-0002-companion-home.md). A rule refusing a member plan that calls
itself an MVP would therefore fire on the first release ever declared and its retrofit would
be seventeen files, so it is a NOTICE naming the count and the files, in the report-then-flip
posture VELDO-0001 established for exactly this case (.veldo/validate_checks.py:930-942).
What IS refused is the collision that needs no retrofit: two releases both declaring
`kind: mvp`, because at most one artifact may claim to be the MVP and the word now lives at
the release level.
"""
import hashlib
import re
from pathlib import Path

SCHEMA = "veldo.release/v1"

# The artifact id shapes. A release id and a plan id are DIFFERENT shapes on purpose: the type
# rule below is what terminates the member recursion, and it can only do that if the two
# vocabularies cannot be confused for each other.
RELEASE_ID_RE = re.compile(r"REL-\d+")
PLAN_ID_RE = re.compile(r"PLAN-\d+")
# The shape the plan contract already types a SPEC id with (.veldo/validate.py:546-547), read
# here only so a member pointing at a spec is refused with the reason NAMED rather than as a
# generic bad id: a spec binds to a plan and never to a release.
SPEC_ID_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*-\d+")

# Every required field, refused SEPARATELY and by name. The list is the contract: a release
# that groups plans must say what it is (schema, id, title), where it stands (status,
# revision), who answers for it (owner), what done is called (milestone), and what is in it
# (members).
REQUIRED_FIELDS = ("schema", "id", "title", "status", "revision", "owner", "milestone",
                   "members")

# The lifecycle, mirroring PLAN_STATUSES (.veldo/validate.py:37) because a release and a plan
# move through the same states and two vocabularies for one ladder is a drift waiting to
# happen.
STATUSES = {"draft", "ready", "in_progress", "released", "closed"}

# What kind of release this is. OPTIONAL, so an ordinary release declares nothing and no
# existing artifact is retrofitted; `mvp` is the only word the contract gives meaning to, and
# at most one release may claim it.
KINDS = {"release", "mvp"}
MVP = "mvp"

# The member kinds, and the whole of the floor rule: a member is another release or a plan,
# and a plan is where the recursion stops. THIS IS THE LOAD-BEARING LEG - the graph rules
# below only terminate because this gives the walk a floor.
#
# ONE TABLE, so the vocabulary and the id shape it implies cannot disagree: a kind IS an entry
# with a typed id shape, and MEMBER_KINDS is derived from it rather than typed twice.
MEMBER_ID_RE = {"release": RELEASE_ID_RE, "plan": PLAN_ID_RE}
MEMBER_KINDS = set(MEMBER_ID_RE)

# A file whose name begins with this is the template, and the registry excludes it exactly as
# plan_registry does (.veldo/validate.py:658-659).
TEMPLATE_PREFIX = "TEMPLATE"

# A digest that BINDS is the full sha256, all 64 lowercase hex characters: the width this
# repository already uses everywhere a digest binds rather than labels.
DIGEST_RE = re.compile(r"[0-9a-f]{64}")

# ---------------------------------------------------------------------------------------
# THE CAUSE TAXONOMY. Named, distinguishable causes rather than one undifferentiated
# invalid-release line, so a reader knows which member to fix, and so a suite can assert the
# taxonomy without matching on a message somebody may reword.
# ---------------------------------------------------------------------------------------
CAUSE_UNREADABLE = "unreadable_front_matter"
CAUSE_MISSING_FIELD = "missing_field"
CAUSE_BAD_SCHEMA = "bad_schema"
CAUSE_BAD_ID = "bad_id"
CAUSE_BAD_STATUS = "bad_status"
CAUSE_BAD_KIND = "bad_kind"
CAUSE_BAD_REVISION = "bad_revision"
CAUSE_UNAPPROVED = "unapproved_past_draft"
CAUSE_MEMBER_SHAPE = "member_shape"
CAUSE_MEMBER_KIND = "unknown_member_kind"
CAUSE_MEMBER_TARGET_TYPE = "member_target_wrong_artifact_type"
CAUSE_MEMBER_DECLARED_TWICE = "member_declared_twice"
CAUSE_MEMBER_CYCLE = "member_cycle"
CAUSE_MEMBER_CLAIMED_TWICE = "member_claimed_by_two_releases"
CAUSE_DUPLICATE_RELEASE_ID = "duplicate_release_id"
CAUSE_DUPLICATE_PLAN_ID = "duplicate_plan_id"
CAUSE_MVP_COLLISION = "two_releases_claim_mvp"

CAUSES = {
    CAUSE_UNREADABLE, CAUSE_MISSING_FIELD, CAUSE_BAD_SCHEMA, CAUSE_BAD_ID, CAUSE_BAD_STATUS,
    CAUSE_BAD_KIND, CAUSE_BAD_REVISION, CAUSE_UNAPPROVED, CAUSE_MEMBER_SHAPE,
    CAUSE_MEMBER_KIND, CAUSE_MEMBER_TARGET_TYPE, CAUSE_MEMBER_DECLARED_TWICE,
    CAUSE_MEMBER_CYCLE, CAUSE_MEMBER_CLAIMED_TWICE, CAUSE_DUPLICATE_RELEASE_ID,
    CAUSE_DUPLICATE_PLAN_ID, CAUSE_MVP_COLLISION,
}

# The two stand-down conditions, as the exact strings the report carries and the gate prints,
# so a reader can tell WHICH one stood the check down without reading this source.
STAND_DOWN_NO_DIRECTORY = "no releases directory at all"
STAND_DOWN_EMPTY_REGISTRY = ("a releases directory that declares no release at all (the template "
                             "is excluded from it, as plan_registry excludes it)")

# The report's key shape. A stood-down report carries EVERY one of these keys, so a reader
# consuming the report never branches on which shape they were handed.
REPORT_KEYS = ("stood_down", "stand_down", "releases", "members", "members_by_kind",
               "members_resolved", "members_unelaborated", "member_records", "duplicate_ids",
               "digest_coverage", "problems", "notices")

_FM_RE = re.compile(r"^---\n(.*?)\n---", re.S)


# ---------------------------------------------------------------------------------------
# READING: one parser, one enumeration, one duplicate rule.
# ---------------------------------------------------------------------------------------
def front_matter(path, parse):
    """(front matter, problem) for one artifact file, read through the ONE parser handed in.

    Exactly one of the two is None. The problem is a sentence, not an exception, because a
    corpus check must report every bad file rather than dying on the first one."""
    try:
        text = Path(path).read_text()
    except OSError as e:
        return None, "cannot be read: %s" % e
    m = _FM_RE.match(text)
    if not m:
        return None, "no YAML front matter"
    try:
        fm = parse(m.group(1))
    except ValueError as e:
        return None, "front matter outside the contract subset: %s" % e
    if not isinstance(fm, dict):
        return None, "front matter is not a mapping of fields"
    return fm, None


def artifact_files(directory):
    """The corpus of one flat artifact directory: every *.md except the template.

    THE ONE ENUMERATION, and it applies the SAME exclusion plan_registry applies
    (.veldo/validate.py:658-659), so the release registry, the plan-side duplicate accessor
    and that registry all read the same file set. An absent directory is an empty corpus, not
    an error: adoption safety is a property of the reader, not of a caller remembering to
    check."""
    d = Path(directory)
    if not d.is_dir():
        return []
    return [p for p in sorted(d.glob("*.md")) if not p.name.startswith(TEMPLATE_PREFIX)]


def id_paths(paths, parse):
    """{declared id: [path, ...]} over artifact files: the ONE mapping the duplicate rule eats.

    A file with no readable front matter or no id is skipped, exactly as plan_registry skips
    it, so this mapping describes the same set that registry describes and the two cannot
    disagree about what is in the corpus. The value is a LIST because that is the whole point:
    a mapping that kept one path per id is the shipped defect."""
    out = {}
    for p in paths:
        fm, _problem = front_matter(p, parse)
        if fm is None:
            continue
        aid = fm.get("id")
        if isinstance(aid, str) and aid.strip():
            out.setdefault(aid, []).append(Path(p))
    return out


def duplicate_ids(mapping):
    """[(id, [filename, ...])] for every id declared by more than one file.

    THE ONE RULE, FOR BOTH REGISTRIES. It takes the id-to-paths mapping rather than a
    directory precisely so a release-side copy cannot exist: a second copy would be a defect
    even while the two copies agreed, because they will not stay agreed. Every colliding id is
    named with EVERY file that declared it, because "one of these vanished" is not an
    actionable refusal."""
    return [(aid, [p.name for p in paths])
            for aid, paths in sorted(mapping.items()) if len(paths) > 1]


def release_registry(releases_dir, parse):
    """{id: {"path": Path, "fm": dict}} for every release file.

    DELIBERATELY THE SHAPE OF plan_registry (.veldo/validate.py:652-670), including that it
    does not raise and that a colliding id resolves to whichever file sorted last: a reader
    that started raising would redden the gate far from the defect. The collision is not
    swallowed, it is exposed through release_duplicate_ids and refused at the corpus check."""
    reg = {}
    for p in artifact_files(releases_dir):
        fm, _problem = front_matter(p, parse)
        if fm is None:
            continue
        rid = fm.get("id")
        if isinstance(rid, str) and rid.strip():
            reg[rid] = {"path": p, "fm": fm}
    return reg


def release_duplicate_ids(releases_dir, parse):
    """Every release id declared by more than one file, with every file that declared it."""
    return duplicate_ids(id_paths(artifact_files(releases_dir), parse))


def plan_duplicate_ids(plans_dir, parse):
    """Every plan id declared by more than one file, with every file that declared it.

    THE SEPARATE ACCESSOR the plan registry gets instead of a changed return shape. It reads
    the same files plan_registry reads, with the same template exclusion, and its result is
    asserted EQUAL to that registry's id set over the live corpus, so this is a second
    ACCESSOR and not a second spelling of the corpus."""
    return duplicate_ids(id_paths(artifact_files(plans_dir), parse))


def member_digest(path):
    """The sha256 of a member's FILE BYTES, all 64 hex characters: what a member is BOUND by.

    NOT plan_hash. plan_hash (.veldo/plan.py:216-222) hashes parsed front matter with volatile
    keys dropped and truncates to 16 hex, so it cannot see a body at all; a receipt built on it
    is a fiction whichever item writes it. This reads bytes the way
    .veldo/request_reconcile.py:131-139 reads them and keeps the full width, because that is
    the width this house uses where a digest BINDS a decision rather than labelling an
    artifact for a human to eyeball.

    None when the file cannot be read, never an empty string: an unresolved member carries no
    figure at all, exactly as the estimation layer prints None rather than a confident zero."""
    try:
        blob = Path(path).read_bytes()
    except OSError:
        return None
    return hashlib.sha256(blob).hexdigest()


def _members(fm):
    """The declared member list, or [] when the field is absent or not a list. The shape
    refusal is record_problems' job; every other reader wants a list it can walk."""
    mem = fm.get("members")
    return mem if isinstance(mem, list) else []


# ---------------------------------------------------------------------------------------
# ONE RECORD: every required field refused by name, then the member type rule.
# ---------------------------------------------------------------------------------------
def _target_type_message(where, kindm, target):
    """The refusal for a member whose target id shape belongs to another artifact type.

    THE OTHER MEMBER SHAPES ARE TESTED FIRST, and this lives in its own function so
    record_problems does not grow another branch (its complexity is already a recorded finding).
    SPEC_ID_RE is a superset of both member vocabularies, so asking it first told an author who
    swapped kind and target between the two levels - the likeliest mistake in this contract -
    that PLAN-9101 "is a spec id", and then explained a rule about specs that does not apply to
    their file. A refusal that misnames the id's type is worse than a generic one, because the
    author goes looking for the wrong thing. The spec-id sentence is reached only when no member
    shape matches, which is what it was written for."""
    other = [k for k, rx in sorted(MEMBER_ID_RE.items())
             if k != kindm and rx.fullmatch(target)]
    if other:
        return ("%s (kind %s) targets %s, which is a %s id: the kind and the target disagree, so "
                "either the kind is wrong or the target is" % (where, kindm, target, other[0]))
    if SPEC_ID_RE.fullmatch(target):
        return ("%s (kind %s) targets %s, which is a spec id: a spec binds to a plan and never to "
                "a release, and the plan contract already types that id shape"
                % (where, kindm, target))
    return ("%s (kind %s) targets %r, which is not a %s id"
            % (where, kindm, target, MEMBER_ID_RE[kindm].pattern))


def record_problems(path, fm):
    """[(subject, cause, message)] for ONE release record's own fields and members.

    The subject is the artifact file, so every refusal names the file, and a member's refusal
    also names the member by its position and its target: a refusal an author cannot locate is
    a refusal they route around."""
    out = []
    subject = str(path)

    # THE REQUIRED-FIELD LOOP. Each missing field is a separate refusal naming the field: one
    # line per thing to fix, never one line saying the record is invalid. An empty members list
    # is a MISSING members declaration, because a release that groups nothing is not a release.
    for field in REQUIRED_FIELDS:
        if field not in fm or fm.get(field) in (None, "", []):
            out.append((subject, CAUSE_MISSING_FIELD,
                        "missing front-matter field: %s" % field))

    if fm.get("schema") not in (None, SCHEMA):
        out.append((subject, CAUSE_BAD_SCHEMA,
                    "bad schema: %r (want %s)" % (fm.get("schema"), SCHEMA)))
    rid = fm.get("id")
    if rid is not None and not RELEASE_ID_RE.fullmatch(str(rid)):
        out.append((subject, CAUSE_BAD_ID, "bad release id: %r (want REL-nnnn)" % (rid,)))
    status = fm.get("status")
    if status and status not in STATUSES:
        out.append((subject, CAUSE_BAD_STATUS,
                    "bad status: %s (allowed: %s)" % (status, sorted(STATUSES))))
    kind = fm.get("kind")
    if kind is not None and kind not in KINDS:
        out.append((subject, CAUSE_BAD_KIND,
                    "bad kind: %r (allowed: %s, and the field is optional)"
                    % (kind, sorted(KINDS))))
    rev = fm.get("revision")
    if "revision" in fm and not (isinstance(rev, int) and not isinstance(rev, bool) and rev >= 1):
        out.append((subject, CAUSE_BAD_REVISION, "revision must be an integer >= 1"))
    # THE SAME WORDS THE PLAN CONTRACT REFUSES THIS IN (.veldo/validate.py:500-503), because a
    # release that groups approved plans cannot itself leave draft on nobody's signature.
    if status and status in STATUSES and status != "draft":
        for field in ("approved_by", "approved_at"):
            if not fm.get(field):
                out.append((subject, CAUSE_UNAPPROVED,
                            "status %s requires %s: a release leaves draft only by a recorded "
                            "human approval" % (status, field)))

    mem = fm.get("members")
    if mem is not None and not isinstance(mem, list):
        out.append((subject, CAUSE_MEMBER_SHAPE,
                    "members must be a list of {kind, target} entries, got %s"
                    % type(mem).__name__))
    seen = {}
    for n, entry in enumerate(_members(fm), 1):
        where = "member %d" % n
        if not isinstance(entry, dict):
            out.append((subject, CAUSE_MEMBER_SHAPE,
                        "%s must be a mapping declaring kind and target, got %r" % (where, entry)))
            continue
        kindm, target = entry.get("kind"), entry.get("target")
        if not (isinstance(target, str) and target.strip()):
            out.append((subject, CAUSE_MEMBER_SHAPE,
                        "%s declares no target: a member with no target is a group with a hole "
                        "in it" % where))
            target = None
        # THE FLOOR IS A TYPE. An unknown kind is refused, and the target shape is NOT then
        # guessed at: without a known kind there is no shape to check the target against, and
        # inventing one would be the machine deciding what the author meant. TWO INDEPENDENT
        # TESTS, each stating its own precondition rather than an if/elif chain, so deleting
        # either one leaves the other reporting exactly what it always reported.
        shape = MEMBER_ID_RE.get(kindm)
        if shape is None:
            out.append((subject, CAUSE_MEMBER_KIND,
                        "%s declares kind %r: a member is one of %s, and a plan is the floor "
                        "the recursion stops on" % (where, kindm, sorted(MEMBER_KINDS))))
        if shape is not None and target is not None and not shape.fullmatch(target):
            # NAME THE TYPE THE TARGET ACTUALLY IS. The three-way choice lives in
            # _target_type_message, which states why the order of its tests is the load-bearing part.
            out.append((subject, CAUSE_MEMBER_TARGET_TYPE,
                        _target_type_message(where, kindm, target)))
        if target is not None:
            if target in seen:
                out.append((subject, CAUSE_MEMBER_DECLARED_TWICE,
                            "%s repeats target %s, already declared as member %d"
                            % (where, target, seen[target])))
            else:
                seen[target] = n
    return out


# ---------------------------------------------------------------------------------------
# THE MEMBER GRAPH: a forest, with no cap on its depth.
# ---------------------------------------------------------------------------------------
def _release_edges(records):
    """{release id: [release id, ...]} over members of kind release that RESOLVE.

    Only resolving targets become edges: an unelaborated member is a member whose file does not
    exist yet, and a graph cannot contain a node nothing declares."""
    edges = {}
    for rid, rec in records.items():
        outs = []
        for entry in _members(rec["fm"]):
            if not isinstance(entry, dict) or entry.get("kind") != "release":
                continue
            t = entry.get("target")
            if isinstance(t, str) and t in records:
                outs.append(t)
        edges[rid] = outs
    return edges


def member_cycles(records):
    """Every member ring, each as the ids in the order the ring closes.

    Iterative depth-first search in deterministic order, the same shape the plan contract's
    DAG check uses (.veldo/validate.py:565-588). NO CONSTANT CAPS THE DEPTH: the walk
    terminates because a plan member is a leaf by TYPE, not because a maximum was declared, and
    a declared maximum would be exactly the size heuristic this layer exists to remove."""
    edges = _release_edges(records)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in edges}
    rings, seen = [], set()
    for start in sorted(edges):
        if color[start] != WHITE:
            continue
        stack = [(start, iter(sorted(edges[start])))]
        walk = [start]
        color[start] = GRAY
        while stack:
            node, it = stack[-1]
            advanced = False
            for nxt in it:
                state = color.get(nxt, BLACK)
                if state == GRAY:
                    ring = walk[walk.index(nxt):] + [nxt]
                    if tuple(ring) not in seen:
                        seen.add(tuple(ring))
                        rings.append(ring)
                elif state == WHITE:
                    color[nxt] = GRAY
                    stack.append((nxt, iter(sorted(edges[nxt]))))
                    walk.append(nxt)
                    advanced = True
                    break
            if not advanced:
                color[node] = BLACK
                stack.pop()
                walk.pop()
    return rings


def member_claims(records):
    """{target id: [release id, ...]} - who claims each member, so single parentage is a
    refusal rather than a convention. Sorted, so a refusal names the same two releases in the
    same order on every machine.

    ONE ENTRY PER RELEASE, NEVER ONE PER MEMBER ENTRY. A release that declares the same target
    twice has ONE authoring mistake, and it already has its own named refusal
    (member_declared_twice). Counting the repeat here too produced a SECOND refusal claiming the
    member has two parents and naming one release twice ("claimed as a member by 2 releases:
    REL-1, REL-1"), which is factually false and inflates one mistake into two errors. The claim
    is therefore made by the DISTINCT targets of each release."""
    claims = {}
    for rid in sorted(records):
        claimed = set()
        for entry in _members(records[rid]["fm"]):
            if isinstance(entry, dict) and isinstance(entry.get("target"), str):
                target = entry["target"]
                if target in claimed:
                    continue
                claimed.add(target)
                claims.setdefault(target, []).append(rid)
    return claims


# ---------------------------------------------------------------------------------------
# THE CORPUS: one problem enumeration, one report, one refusal.
# ---------------------------------------------------------------------------------------
def _plan_records(plans_dir, parse):
    """{plan id: {"path", "fm", "paths"}} for the plan corpus, where "paths" is EVERY file that
    declared the id. Built from the one enumeration, so a member resolving through it sees the
    same corpus the plan registry sees and can also see when that id is ambiguous."""
    out = {}
    for pid, paths in id_paths(artifact_files(plans_dir), parse).items():
        fm, _problem = front_matter(paths[-1], parse)
        out[pid] = {"path": paths[-1], "fm": fm or {}, "paths": paths}
    return out


def release_problems(releases_dir, plans_dir, parse):
    """[(subject, cause, message)] - THE ONE PROBLEM ENUMERATION.

    Both surfaces consume this: release_report prints it as data and check_release refuses
    through it, so the reporting form and the refusing form cannot disagree about what is
    wrong. Every entry names the artifact file it is about, or the corpus directory when the
    problem is a collision between files."""
    d = str(Path(releases_dir))
    files = artifact_files(releases_dir)
    problems = []

    for rid, names in duplicate_ids(id_paths(files, parse)):
        problems.append((d, CAUSE_DUPLICATE_RELEASE_ID,
                         "duplicate release id %s declared by %d files: %s. One of them "
                         "disappears from every derived view, so neither is trusted"
                         % (rid, len(names), ", ".join(sorted(names)))))

    records = {}
    for p in files:
        fm, problem = front_matter(p, parse)
        if fm is None:
            problems.append((str(p), CAUSE_UNREADABLE, problem))
            continue
        problems.extend(record_problems(p, fm))
        rid = fm.get("id")
        if isinstance(rid, str) and rid.strip():
            records[rid] = {"path": p, "fm": fm}

    plans = _plan_records(plans_dir, parse)

    # A member binding to an AMBIGUOUS plan id: the release cannot say which file it grouped.
    # This is the release-side face of the duplicate-id defect, and it is a different fact from
    # the plan corpus carrying a duplicate at all, which check_plan_ids refuses on its own.
    for rid in sorted(records):
        for n, entry in enumerate(_members(records[rid]["fm"]), 1):
            if not isinstance(entry, dict) or entry.get("kind") != "plan":
                continue
            t = entry.get("target")
            paths = plans.get(t, {}).get("paths") or []
            if len(paths) > 1:
                problems.append((str(records[rid]["path"]), CAUSE_DUPLICATE_PLAN_ID,
                                 "member %d targets plan %s, which %d files declare: %s. The "
                                 "member would bind to whichever file sorted last"
                                 % (n, t, len(paths),
                                    ", ".join(sorted(p.name for p in paths)))))

    for ring in member_cycles(records):
        problems.append((str(records[ring[0]]["path"]), CAUSE_MEMBER_CYCLE,
                         "member cycle: %s" % " -> ".join(ring)))

    for target, claimants in sorted(member_claims(records).items()):
        if len(claimants) > 1:
            problems.append((d, CAUSE_MEMBER_CLAIMED_TWICE,
                             "%s is claimed as a member by %d releases: %s. A member has one "
                             "parent or the group is not a forest"
                             % (target, len(claimants), ", ".join(claimants))))

    mvps = sorted(rid for rid in records if records[rid]["fm"].get("kind") == MVP)
    if len(mvps) > 1:
        problems.append((d, CAUSE_MVP_COLLISION,
                         "%d releases declare kind %s: %s. At most one artifact may claim to be "
                         "the MVP" % (len(mvps), MVP, ", ".join(mvps))))
    return problems


def release_notices(releases_dir, plans_dir, parse):
    """[(subject, cause, message)] - what is REPORTED and not refused.

    Today that is exactly one thing: a member plan still declaring the legacy `kind: mvp`. It
    names the COUNT and the FILES it counted, never a bare number, once per release. Refusing
    it would fire on the first release ever declared and retrofit seventeen plan files, which
    is a rule arriving red in a working repository."""
    notices = []
    records = release_registry(releases_dir, parse)
    plans = _plan_records(plans_dir, parse)
    for rid in sorted(records):
        legacy = []
        for entry in _members(records[rid]["fm"]):
            if not isinstance(entry, dict) or entry.get("kind") != "plan":
                continue
            rec = plans.get(entry.get("target"))
            if rec and rec["fm"].get("kind") == MVP:
                legacy.append(rec["path"].name)
        if legacy:
            notices.append((str(records[rid]["path"]), MVP,
                            "NOTICE, not a refusal: %d member plan(s) still declare kind: %s "
                            "(%s). The word MVP now lives at the release level; the plan kind "
                            "is legacy and is reported rather than refused because refusing it "
                            "would retrofit the plan corpus"
                            % (len(legacy), MVP, ", ".join(sorted(legacy)))))
    return notices


def _stood_down(reason, plan_dups):
    """The stand-down report: EVERY key a live report carries, plus the condition that stood the
    check down. Identical between the two conditions except for that one field and for the one
    figure below, so a stand-down can never be mistaken for a live read of an empty corpus.

    EVERY ZERO HERE IS A READING, NOT A CONSTANT, AND THE PLAN HALF IS THE ONE THAT COULD BE
    FALSE. releases, members, members_resolved and the release half of duplicate_ids are zero BY
    CONSTRUCTION: this branch is only reached when the release candidate file set is empty, so
    there is nothing to count. The plan half is a reading of a DIFFERENT corpus, which standing
    the release check down says nothing about, so it is COMPUTED and handed in rather than
    printed as a confident zero. Printing [] there stated that the plan corpus carries no
    duplicate id no matter what it carried, which is the one figure in this report that could be
    a lie, and check_plan_ids refuses that duplicate whether or not any release exists."""
    return {"stood_down": True, "stand_down": reason, "releases": 0, "members": 0,
            "members_by_kind": {}, "members_resolved": 0, "members_unelaborated": 0,
            "member_records": [], "duplicate_ids": {"release": [], "plan": plan_dups},
            "digest_coverage": None, "problems": [], "notices": []}


def release_report(releases_dir, plans_dir, parse):
    """The resolved reading of the release corpus: its own coverage beside every figure.

    ADOPTION SAFE, AND NEVER KEYED ON THE DIRECTORY. Two conditions stand it down and both
    name themselves: no releases directory at all, and a directory that declares no release
    (the template is excluded from the registry, so shipping it declares nothing). Keying on
    the DIRECTORY would silently stop standing down the moment the template landed.

    AND IT IS KEYED ON THE CANDIDATE FILES, NOT ON THE RESOLVED REGISTRY, which is a
    correction found by driving this: a release file that declares NO id, or whose front
    matter the one parser cannot read, leaves the REGISTRY empty while the corpus plainly
    holds a release. Keyed on the registry, that file stood the whole check down and its own
    refusal was never reached, which is a broken artifact passing as an unadopted repository.
    The registry is empty whenever the file set is, so nothing about the two declared
    conditions changes.

    A FIGURE WITH NO BASIS IS NOT PRINTED: an unresolved member carries digest None rather
    than an empty string, and digest_coverage is None rather than a confident 0.0 when no
    member is declared at all. The stood-down branch obeys the same rule: it still READS the
    plan corpus for duplicate ids, because that figure has a basis this branch can reach and a
    constant [] there would be a confident zero about a corpus nobody looked at."""
    d = Path(releases_dir)
    if not artifact_files(d):
        return _stood_down(STAND_DOWN_NO_DIRECTORY if not d.is_dir()
                           else STAND_DOWN_EMPTY_REGISTRY,
                           plan_duplicate_ids(plans_dir, parse))

    records = release_registry(releases_dir, parse)
    plans = _plan_records(plans_dir, parse)
    by_kind, member_records = {}, []
    for rid in sorted(records):
        for n, entry in enumerate(_members(records[rid]["fm"]), 1):
            if not isinstance(entry, dict):
                continue
            kind, target = entry.get("kind"), entry.get("target")
            by_kind[kind] = by_kind.get(kind, 0) + 1
            source = records if kind == "release" else plans
            rec = source.get(target) if isinstance(target, str) else None
            path = rec["path"] if rec else None
            # THE DIGEST IS REACHED HERE, beside the member's id and its path, so the derived
            # view and every later receipt read ONE value rather than each computing its own.
            member_records.append({"release": rid, "position": n, "kind": kind,
                                   "target": target,
                                   "path": str(path) if path else None,
                                   "digest": member_digest(path) if path else None})

    declared = len(member_records)
    resolved = sum(1 for m in member_records if m["digest"] is not None)
    return {
        "stood_down": False, "stand_down": None, "releases": len(records),
        "members": declared, "members_by_kind": by_kind, "members_resolved": resolved,
        "members_unelaborated": declared - resolved, "member_records": member_records,
        "duplicate_ids": {"release": release_duplicate_ids(releases_dir, parse),
                          "plan": plan_duplicate_ids(plans_dir, parse)},
        "digest_coverage": (round(resolved / declared, 3) if declared else None),
        "problems": release_problems(releases_dir, plans_dir, parse),
        "notices": release_notices(releases_dir, plans_dir, parse),
    }


def check_release(releases_dir, plans_dir, parse, fail):
    """The gate entry point over the release corpus: the refusing face of release_problems.

    Adoption safe: an empty registry stands the whole check down, and the stand-down PRINTS one
    line naming which condition it was, because a stand-down that looks like a pass is how an
    unadopted check gets mistaken for a green one. Fail closed the moment a release exists.
    Notices are printed through the same reporter with the posture named IN the line, and are
    NOT counted: a report is migration pressure, not a refusal."""
    report = release_report(releases_dir, plans_dir, parse)
    if report["stood_down"]:
        fail(str(Path(releases_dir)),
             "release check STANDS DOWN, recorded rather than passed: %s" % report["stand_down"])
        return 0
    errs = 0
    for subject, _cause, message in report["problems"]:
        errs += fail(subject, message)
    for subject, _cause, message in report["notices"]:
        fail(subject, message)          # printed, deliberately not counted
    return errs


def check_plan_ids(plans_dir, parse, fail):
    """The plan registry's duplicate refusal, registered SEPARATELY from the release check.

    A duplicate plan id is a defect in the plan corpus whether or not any release exists, so
    this must not stand down with the release check. It changes nothing about plan_registry:
    that reader keeps its return shape and still does not raise, and this names every id
    declared more than once with every file that declared it."""
    errs = 0
    for pid, names in plan_duplicate_ids(plans_dir, parse):
        errs += fail(str(Path(plans_dir)),
                     "duplicate plan id %s declared by %d files: %s. The registry keeps one of "
                     "them, so the other disappears from every derived view"
                     % (pid, len(names), ", ".join(sorted(names))))
    return errs
