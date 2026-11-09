#!/usr/bin/env python3
"""VELDO policy check: the mechanical reader of .veldo/policy.yaml.

Called by the guard before a push/merge is allowed. Exits 0 (allow) or
prints the reason and exits 1 (block). Checks, for the current HEAD:

1. Protected paths: if the commit range being pushed touches a protected
   path, an approval file (veldo.approval/v1) must exist for exactly HEAD,
   unexpired. Anything may raise risk; nothing lowers it.
2. Emergency debt: an emergency.push event without a later backfill-closing
   event (spec.shipped for its backfill, or an explicit emergency.closed)
   blocks ordinary pushes, as the setup promises.
3. VELDO-0272: a lowering of a spec's human_approval from required, judged by
   spec id between the push base and HEAD and in every commit of the push,
   needs an owner approval scoping that spec's files (approval_flag_lowered);
   every spec a push carries needs a passing verdict from a reviewer who is
   not the producer (landing_without_review), and a spec the rule computes
   as required needs the owner's approval as well; a push changing anything
   but spec files and proof bundles needs at least one such spec that is not a draft
   (N3: a draft covers nothing).

Proportionate by design: stdlib only, no yaml dependency (reads the simple
policy.yaml shape the template ships).
"""

# Load the shared Git boundary by sibling path, including when imported by file location.
import importlib.util as _git_importlib
from pathlib import Path as _GitPath

import importlib.util as _yaml_importlib
from pathlib import Path as _YamlPath
_yaml_spec = _yaml_importlib.spec_from_file_location("veldo_yamlish", _YamlPath(__file__).resolve().with_name("yamlish.py"))
_Y = _yaml_importlib.module_from_spec(_yaml_spec)
_yaml_spec.loader.exec_module(_Y)
_git_spec = _git_importlib.spec_from_file_location("veldo_git_process", _GitPath(__file__).resolve().with_name("git_process.py"))
_git_process = _git_importlib.module_from_spec(_git_spec)
_git_spec.loader.exec_module(_git_process)
import datetime, fnmatch, hashlib, importlib.util, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The policy SOURCE, an input separate from the SUBJECT root (VELDO-0058 AC3). ROOT is the tree being
# judged; POLICY is the policy.yaml that says which of its paths are protected. Unset (None) it is the
# subject root's own .veldo/policy.yaml, resolved at the time of the read, so an ordinary run and a
# caller that points ROOT elsewhere behave exactly as before. The installed-policy runner
# (control_verification._policy_main) sets it to the installation's policy.yaml: a candidate judged
# by its own policy.yaml could empty protected_paths and land a protected change with no approval.
POLICY = None


def policy_source():
    """The policy.yaml this run reads: POLICY when set, else the subject root's own."""
    return Path(POLICY) if POLICY is not None else ROOT / ".veldo" / "policy.yaml"


# The range BASE, an input separate from the subject's own refs (VELDO-0058 AC3). Unset (None), the
# base of "what is this push" is computed from the subject root's refs exactly as _range_specs
# describes, so an ordinary run is unchanged. The installed-policy runner
# (control_verification._policy_main) sets it to the trunk commit the lander synced and gated against:
# a candidate whose code runs inside the gate can move its own refs/remotes/origin/main to HEAD, and a
# range computed from those refs is then empty, so a protected change would land with no approval.
# When set, every range read is exactly BASE..HEAD, and one that Git cannot answer is an error, never
# an empty range.
BASE = None

# The proof-corpus enumeration (WARP-0727): the one owner of what a corpus path is, shared
# with .veldo/events.py and .veldo/validate.py. A private glob here would be a THIRD spelling
# of one set, which is the defect that module exists to make unreachable.
_vcspec = importlib.util.spec_from_file_location(
    "veldo_verdict_corpus", ROOT / ".veldo" / "verdict_corpus.py")
_VC = importlib.util.module_from_spec(_vcspec)
_vcspec.loader.exec_module(_VC)


def _corpus_files(pattern):
    """The corpus artifacts of ONE declared pattern, as absolute paths, through the ONE
    enumeration.

    EVERY CORPUS READ IN THIS FILE GOES THROUGH HERE (WARP-0727 round 2). Three private globs
    survived the first round - `proof/*/approval*.json` and two spellings of
    `proof/*/manifest.json` - and each was a SECOND implementation of a set the owner already
    declares a pattern for. They computed the same answer as the owner on this platform, which
    is what makes them a law violation rather than a live divergence: a second spelling is a
    place a future difference can appear where neither side can see it, and the whole point of
    the owner is that there is nowhere for one to appear."""
    return [ROOT / rel for rel in _VC.disk_corpus(ROOT, pattern)]


def _verdict_files():
    """The verdict corpus as absolute paths, through the ONE enumeration."""
    return _corpus_files(_VC.VERDICT_PATTERN)


def protected_patterns():
    policy = _Y.read(policy_source())
    rows = policy.get("protected_paths", [])
    if not isinstance(rows, list) or any(not isinstance(r, dict) or not isinstance(r.get("path"), str) for r in rows):
        raise ValueError("policy protected_paths must be a list of path mappings")
    return [row["path"] for row in rows]


# THE PROTECTED REFS (VELDO-0268). The push guard judges a push or merge only when it moves a ref
# this set names; a working branch is a backup and a review surface, and the gate and approvals
# bind where the trunk moves (at landing, and at any push that moves a protected ref). The set is
# DECLARED in policy.yaml as protected_refs, fnmatch patterns over full ref names, and is the UNION
# of every source that declares it: the working tree's policy, the policy committed at the local
# trunk ref (so a candidate cannot shrink the set by editing its own policy before it pushes main),
# and POLICY when the installed-policy runner sets it. Anything may add a ref; nothing removes one.
# When no source declares the key, every ref is protected: the behaviour before the key existed.
TRUNK_REF = "refs/heads/main"
EVERY_REF = "*"


class ProtectedRefsUnreadable(ValueError):
    """A protected_refs key that is present but cannot be read. The guard refuses the push."""

    def __init__(self, source):
        super().__init__("protected_refs in %s cannot be read" % source)
        self.source = source


def _protected_refs_of(document, source):
    """The patterns one parsed policy declares, or None when it declares no protected_refs key."""
    if not isinstance(document, dict) or "protected_refs" not in document:
        return None
    rows = document["protected_refs"]
    if not isinstance(rows, list) or any(not isinstance(r, str) or not r for r in rows):
        raise ProtectedRefsUnreadable(source)
    return rows


def protected_ref_sources():
    """[(pattern, source)] over every source that declares protected_refs, or None when none does.
    A source that cannot be read where it exists raises ProtectedRefsUnreadable (fail closed)."""
    found = []
    declared = False
    tree = ROOT / ".veldo" / "policy.yaml"
    files = [tree]
    if POLICY is not None and Path(POLICY).resolve() != tree.resolve():
        files.append(Path(POLICY))
    for path in files:
        if not path.exists():
            continue
        try:
            document = _Y.read(path)
        except Exception:
            raise ProtectedRefsUnreadable(str(path))
        rows = _protected_refs_of(document, str(path))
        if rows is not None:
            declared = True
            found += [(r, str(path)) for r in rows]
    trunk = _git_process.run(["git", "rev-parse", "--verify", "--quiet", TRUNK_REF + "^{commit}"],
                             capture_output=True, text=True, cwd=ROOT)
    if trunk.returncode == 0 and trunk.stdout.strip():
        source = "%s:.veldo/policy.yaml" % TRUNK_REF
        listed = _git_process.run(["git", "ls-tree", "--name-only", trunk.stdout.strip(), ".veldo/policy.yaml"],
                                  capture_output=True, text=True, cwd=ROOT)
        if listed.returncode != 0:
            raise ProtectedRefsUnreadable(source)
        if listed.stdout.strip():
            shown = _git_process.run(["git", "show", trunk.stdout.strip() + ":.veldo/policy.yaml"],
                                     capture_output=True, cwd=ROOT)
            try:
                if shown.returncode != 0:
                    raise ValueError(source)
                document = _Y.parse(shown.stdout.decode("utf-8-sig"), source)
            except Exception:
                raise ProtectedRefsUnreadable(source)
            rows = _protected_refs_of(document, source)
            if rows is not None:
                declared = True
                found += [(r, source) for r in rows]
    return found if declared else None


def protected_ref(name):
    """(pattern, source) that makes the full ref name `name` protected, or None when it is not.
    With no source declaring protected_refs every ref is protected: (EVERY_REF, the reason)."""
    sources = protected_ref_sources()
    if sources is None:
        return (EVERY_REF, "no policy declares protected_refs")
    for pattern, source in sources:
        if fnmatch.fnmatchcase(name, pattern):
            return (pattern, source)
    return None


def _protected_ref_main(names):
    """`policy_check.py --protected-ref REF...`: one line per ref, tab separated: the ref, then
    'protected', the pattern and its source, or 'not-protected'. Exit 0; exit 3 with the guard's
    refusal on standard error when protected_refs cannot be read."""
    try:
        for name in names:
            hit = protected_ref(name)
            print("\t".join((name, "protected") + hit) if hit else name + "\tnot-protected")
    except ProtectedRefsUnreadable as error:
        print("VELDO guard: blocked. %s" % error, file=sys.stderr)
        return 3
    return 0


def _range_specs():
    """The comparison bases to try, in order, for "what is this push".

    THE FALLBACK USED TO DECIDE THE ANSWER, and it made the gate irreproducible. Only
    `@{upstream}..HEAD` and `HEAD~20..HEAD` were tried, and a checkout with no upstream - which is
    EVERY git worktree, detached or on a fresh branch - silently fell through to an arbitrary
    twenty-commit window. Measured at one commit on 2026-08-03: the main checkout saw 2 changed
    files and no protected paths, a worktree of the SAME COMMIT saw 39 and four protected ones, so
    the protected-path check demanded approvals for files that were not part of the change and the
    gate went red on a tree whose code was byte-identical to a green one.

    `origin/main` resolves in every clone and every worktree, so trying it BEFORE the twenty-commit
    guess makes the three agree. The guess stays last, for a repository with no origin at all, but
    it is now the exception rather than the thing that answers whenever tracking is not configured.
    """
    if BASE is not None:
        return [str(BASE) + "..HEAD"]
    specs = ["@{upstream}..HEAD"]
    for ref in ("origin/HEAD", "origin/main"):
        r = _git_process.run(["git", "rev-parse", "--verify", "--quiet", ref],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode == 0 and r.stdout.strip():
            specs.append(ref + "..HEAD")
    specs.append("HEAD~20..HEAD")
    return specs


def changed_files():
    # files changed on this branch vs its upstream (see _range_specs for why the order matters)
    for spec in _range_specs():
        r = _git_process.run(["git", "diff", "--name-only", spec],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode == 0:
            return [f for f in r.stdout.splitlines() if f]
    if BASE is not None:
        raise RuntimeError("the push range %s..HEAD cannot be read" % BASE)
    return []


def head():
    r = _git_process.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT)
    return r.stdout.strip()


def push_range_commits():
    """Every commit hash being pushed, HEAD first. Same base resolution as
    changed_files, through `_range_specs`, so the two cannot disagree about what the push is."""
    for spec in _range_specs():
        r = _git_process.run(["git", "rev-list", spec],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode == 0:
            return [c for c in r.stdout.splitlines() if c]
    if BASE is not None:
        raise RuntimeError("the push range %s..HEAD cannot be read" % BASE)
    return []


def glob_covers(path, pat):
    """THE ONE fnmatch reading of a protected pattern: the pattern as written, or with its trailing
    stars widened to one, so "dir/*" also covers a file deeper under dir/. The push check, the
    approval scope and the computed approval flag (VELDO-0272) all read a pattern this way."""
    return fnmatch.fnmatch(path, pat) or fnmatch.fnmatch(path, pat.rstrip("*") + "*")


# --- VELDO-0272: the approval flag a spec's placement computes ------------------------------------
# The owner's approval follows a spec's footprint and risk areas, not its author's word. The rule is
# here, beside the protected list it reads, and the validator and executor.merge_ready load it from
# here, so the three cannot disagree about what "required" means.
APPROVAL_AREAS = ("money", "auth_security", "schema", "irreversible_infra")


def globs_meet(a, b):
    """A footprint entry and a protected path match each other: either glob matches the other."""
    return glob_covers(a, b) or glob_covers(b, a)


def declared_flag(fm):
    """The human_approval a spec declares: required unless it says not_required (absent reads as
    not_required, as the index and the executor have always read it)."""
    words = str((fm or {}).get("human_approval", "not_required")).split()
    return "not_required" if words and words[0] == "not_required" else "required"


def approval_bases(fm, patterns=None):
    """Every basis on which the rule computes approval REQUIRED for this front matter; an empty list
    is not_required. Bases: each protected path a footprint entry meets, a non-empty protected_paths,
    each risk area naming money, auth_security, schema or irreversible_infra, and an absent footprint
    (a spec that declares no footprint has not said it stays off the protected list)."""
    fm = fm or {}
    pats = protected_patterns() if patterns is None else patterns
    bases = []
    footprint = fm.get("footprint")
    if isinstance(footprint, str):
        footprint = [footprint]
    if not isinstance(footprint, list) or not footprint:
        bases.append("footprint absent")
    else:
        for entry in footprint:
            for pat in pats:
                if isinstance(entry, str) and globs_meet(entry, pat):
                    bases.append("protected path %s (footprint %s)" % (pat, entry))
    if fm.get("protected_paths"):
        bases.append("protected_paths declared %s" % (fm.get("protected_paths"),))
    areas = fm.get("risk_areas")
    for area in areas if isinstance(areas, list) else []:
        if area in APPROVAL_AREAS:
            bases.append("risk area %s" % area)
    return bases


def effective_flag(fm, patterns=None):
    """required when the spec declares it or the rule computes it; a declaration can raise the flag,
    never lower it."""
    if declared_flag(fm) == "required" or approval_bases(fm, patterns):
        return "required"
    return "not_required"


_SPEC_FILE = re.compile(r"specs/([A-Z]+-\d+)-[^/]*\.md$")
_PROOF_FILE = re.compile(r"proof/([A-Z]+-\d+)/")


def _spec_names(rev, cache):
    """{spec id: [spec file names]} in the tree of `rev`, keyed by the id in the file name, or None when
    Git cannot list that tree. Cached per revision for one check."""
    if rev not in cache:
        r = _git_process.run(["git", "ls-tree", "--name-only", rev, "specs/"],
                             capture_output=True, text=True, cwd=ROOT)
        names = None
        if r.returncode == 0:
            names = {}
            for name in r.stdout.splitlines():
                m = _SPEC_FILE.match(name)
                if m:
                    names.setdefault(m.group(1), []).append(name)
        cache[rev] = names
    return cache[rev]


def _flag_state(rev, sid, cache):
    """(state, names) of spec `sid` at `rev`: state is required, not_required, absent (no spec file of
    that id) or unreadable (Git cannot read the tree or the file, more than one file carries the id, or
    the front matter does not parse). Keyed by id, never by path, so a rename is the same spec."""
    by_id = _spec_names(rev, cache)
    if by_id is None:
        return "unreadable", []
    names = by_id.get(sid, [])
    if not names:
        return "absent", []
    if len(names) != 1:
        return "unreadable", names
    r = _git_process.run(["git", "show", "%s:%s" % (rev, names[0])], capture_output=True, cwd=ROOT)
    if r.returncode != 0:
        return "unreadable", names
    try:
        fm = _Y.front_matter(r.stdout.decode("utf-8"), names[0])
    except Exception:
        return "unreadable", names
    return (declared_flag(fm), names) if isinstance(fm, dict) else ("unreadable", names)


def _lowers(now, before):
    """A change from the `before` states (one per real parent, or the push base) to `now` lowers the
    flag when `now` is lower than the value on EVERY before that has the spec: `now` is not required,
    at least one before has the spec (a before where it is absent is no value to lower), and every
    before that has it is required or unreadable (FAIL CLOSED: a value that cannot be read counts as
    required, so a lowering through a broken or deleted spec is still a lowering). A merge that takes
    a value one side already has lowers nothing itself (VELDO-0272 M1), and that includes a side where the
    spec is absent: a merge taking trunk's retirement or renumbering of a spec takes a state trunk already
    has, so the `now in before` test reads the raw parent states BEFORE the absent ones are set aside
    (fix round 5, F1)."""
    if now == "required" or now in before:
        return False
    before = [b for b in before if b != "absent"]
    return bool(before) and all(b in ("required", "unreadable") for b in before)


def _parents(c):
    r = _git_process.run(["git", "rev-list", "--parents", "-n", "1", c], capture_output=True, text=True, cwd=ROOT)
    words = r.stdout.split() if r.returncode == 0 else []
    if not words:
        raise RuntimeError("the parents of %s cannot be read" % c)
    return words[1:]


def _changed_ids(a, b, cache):
    """The spec ids whose files differ between trees a and b, renames off (a rename shows both names,
    and both carry the id). When Git cannot answer, every id in either tree (fail closed)."""
    r = _git_process.run(["git", "diff-tree", "-r", "--name-only", "--no-renames", a, b, "--", "specs/"],
                         capture_output=True, text=True, cwd=ROOT)
    if r.returncode == 0:
        return {m.group(1) for m in (_SPEC_FILE.match(n) for n in r.stdout.splitlines()) if m}
    ids = set()
    for rev in (a, b):
        ids |= set(_spec_names(rev, cache) or {})
    return ids


def push_range():
    """(commits, bases): every commit being pushed, HEAD first (rev-list over the same `_range_specs`, so
    it cannot disagree with push_range_commits), and the push base: the ONE commit the range is measured
    from, the protected ref's current tip (BASE, or the ref `_range_specs` resolved). VELDO-0272 N1: never
    every boundary commit, because a merge whose second parent is an old trunk commit puts a pre-raise
    state among the boundaries, and a lowering judged against any ancestor is no lowering at all. A tip
    that cannot be resolved for a range that can be read is an error (FAIL CLOSED). With no readable
    range and no BASE, the range is HEAD and the bases are its parents."""
    for spec in _range_specs():
        r = _git_process.run(["git", "rev-list", spec], capture_output=True, text=True, cwd=ROOT)
        if r.returncode == 0:
            commits = [l for l in r.stdout.splitlines() if l]
            left = spec[:-len("..HEAD")]
            t = _git_process.run(["git", "rev-parse", "--verify", "--quiet", left + "^{commit}"],
                                 capture_output=True, text=True, cwd=ROOT)
            tip = t.stdout.strip() if t.returncode == 0 else ""
            if not tip:
                raise RuntimeError("the push base %s cannot be resolved" % left)
            return commits, [tip]
    if BASE is not None:
        raise RuntimeError("the push range %s..HEAD cannot be read" % BASE)
    h = head()
    return [h], _parents(h)


def lowered_flags(commits, bases):
    """[(spec id, commit, spec file names)]: every lowering of a spec's human_approval from required
    (approval_flag_lowered unless the owner scoped its files). VELDO-0272 F1: judged by spec ID, so a
    rename, a delete and re-add, or a two-step lowering through an unreadable state is seen, (1) between
    the push base and HEAD, which is what lands, and (2) per commit in the range, merges included, which
    is the AC's per-commit reading. A base value that cannot be read counts as required (fail closed).
    VELDO-0272 N1: the push base is the protected ref's current tip, so an old trunk commit (a state from
    before a raise) is never a value the landed state is measured against. VELDO-0272 M1: a commit is
    judged only for the spec ids it changed against its REAL parents, and against those parents (a merge
    against every parent), never against the tip: a branch commit made before trunk added or raised a
    spec did not lower it, and an honest merge of trunk keeps trunk's value."""
    cache = {}
    out = []
    seen = set()

    def judge(target, befores):
        ids = set()
        for b in befores:
            ids |= _changed_ids(b, target, cache)
        for sid in sorted(ids):
            now, names = _flag_state(target, sid, cache)
            states = [_flag_state(b, sid, cache) for b in befores]
            if _lowers(now, [s for s, _ in states]):
                files = sorted(set(names).union(*[set(n) for _, n in states]))
                key = (sid, target)
                if key not in seen:
                    seen.add(key)
                    out.append((sid, target, files))

    if commits and bases:
        judge(head(), bases)
    for c in commits:
        befores = _parents(c)
        if befores:
            judge(c, befores)
    # VELDO-0287 (d): an id absent at the push base and at HEAD never reached main (a draft renumbered
    # inside the push), so nothing on main loses its approval through it.
    tip = head()
    return [x for x in out if not (bases and _flag_state(tip, x[0], cache)[0] == "absent"
                                   and all(_flag_state(b, x[0], cache)[0] == "absent" for b in bases))]


_PROJECTIONS = []


def _projection_paths():
    """The derived files the lander regenerates (lander.PROJECTIONS, today specs/index.md), read from the
    lander beside this file so the set is spelled once. When the lander cannot be read, none: a derived
    file then counts as work (fail closed). The assignment is read as a literal from the lander's source,
    never by executing the lander, whose module load pulls its siblings and the uuid and platform chain
    into every policy run (the isolated-enforcement entry, VELDO-0043, refuses platform's _wmi probe)."""
    if not _PROJECTIONS:
        try:
            import ast
            tree = ast.parse(Path(__file__).resolve().with_name("lander.py").read_text())
            value = next(node.value for node in tree.body if isinstance(node, ast.Assign)
                         and any(isinstance(t, ast.Name) and t.id == "PROJECTIONS" for t in node.targets))
            _PROJECTIONS.append(frozenset(path for path, _generator in ast.literal_eval(value)))
        except Exception:
            _PROJECTIONS.append(frozenset())
    return _PROJECTIONS[0]


def _approval_record(f):
    """A file of the approval corpus (proof/<one directory>/approval*.json), the set valid_approval_for
    reads: an owner's decision, judged by approval_refusal wherever it authorizes something."""
    return _VC.corpus_member(f, _VC.APPROVAL_PATTERN)


def _not_work(f):
    """VELDO-0272 fix round 5 (F2): a spec file, a file of a spec's proof bundle, a derived projection or an
    approval record is not work for the reviewed-spec coverage rule (N3). Any other file under specs/ or
    proof/ (a script, a loose note) is work like any other (fix round 4)."""
    return bool(_SPEC_FILE.match(f) or _PROOF_FILE.match(f) or f in _projection_paths() or _approval_record(f))


def spec_only(files):
    """True when a push changes only spec files, derived projections and approval records: no proof
    manifest, verdict or other bundle file, and no work. Such a push lands no work, so no review of it can
    exist yet (fix round 5)."""
    return bool(files) and all(_SPEC_FILE.match(f) or f in _projection_paths() or _approval_record(f) for f in files)


def committer_identities(commits):
    """The committer names and emails of `commits`, as one list for the self-approval test, or "" when
    none can be read (fail closed)."""
    out = []
    for i in range(0, len(commits), 200):
        r = _git_process.run(["git", "show", "-s", "--format=%cn%x00%ce"] + list(commits[i:i + 200]),
                             capture_output=True, text=True, cwd=ROOT)
        if r.returncode != 0:
            return ""
        for line in r.stdout.splitlines():
            out += [w for w in line.split("\0") if w.strip()]
    return out if _identities(out) else ""


def approval_producer(producer, files, commits):
    """The identity an approval in this push must not share (fix round 5). A determined producer is kept.
    A producer that cannot be determined, in a push that changes only spec files (spec_only), is replaced by
    the push's committer identities: an owner approval of a spec-only change (a spec moved to ready, a
    re-mark) has no producer, because nothing it covers has proof. In any other push a missing producer
    stays missing, and every approval is refused (N2)."""
    if _identities(producer) or not spec_only(files):
        return producer
    return committer_identities(commits)


def push_specs(files):
    """The spec ids a push carries: each spec file and each proof bundle it changes."""
    ids = set()
    for f in files:
        m = _SPEC_FILE.match(f) or _PROOF_FILE.match(f)
        if m:
            ids.add(m.group(1))
    return sorted(ids)


def _identities(who):
    """The normalized identities a producer or reviewer field names: a string with its whitespace
    collapsed and its case folded; a mapping or a list, every string inside it. Empty when it names
    nobody. VELDO-0272 F2: a reviewer stored as a mapping is compared by what it names, never by its type."""
    if isinstance(who, str):
        flat = " ".join(who.split()).casefold()
        return {flat} if flat else set()
    if isinstance(who, dict):
        parts = list(who.values())
    elif isinstance(who, (list, tuple)):
        parts = list(who)
    else:
        return set()
    out = set()
    for part in parts:
        out |= _identities(part)
    return out


def _self_review(reviewer, producer):
    """True when a verdict cannot count as an independent review (FAIL CLOSED): no producer is
    recorded, so independence cannot be established; the verdict names no reviewer; or the reviewer
    and the producer share a normalized identity."""
    if not _identities(producer):
        return True
    if not _identities(reviewer):
        return True
    return bool(_identities(reviewer) & _identities(producer))


def reviewed_landing(spec_id, commits):
    """The verdict a not-required spec lands on (VELDO-0272 AC3 b), or None: pass or pass_with_notes,
    no blocking findings, bound to a commit in the push range and to the spec's CURRENT proof digest
    (valid_verdict_for), from a reviewer who is not the proof producer. The limit is the merge rule's:
    a verdict is a file an agent can write, so the reviewer identity check and the daily summary make
    a forged review visible, not impossible."""
    producer = producer_for(spec_id)
    for c in commits:
        found = valid_verdict_for(c, spec_id=spec_id, bound=True, producer=producer)
        if found:
            return found
    return None


def _approval_covers(approval, path):
    """Path-scoped authorization: an approval only authorizes the paths its
    scope names. Empty scope.paths authorizes nothing (fail closed) - name the
    paths."""
    for pat in approval.get("scope", {}).get("paths", []) or []:
        if glob_covers(path, pat):
            return True
    return False


def owner_approved(spec_id, commits, producer=None):
    """An owner approval of an approval-required spec (VELDO-0272 AC3, judged per spec): bound to a
    commit in the push, not self approved, naming the spec by scope.spec_id or covering its spec file.
    With no spec file at HEAD, only scope.spec_id can name it. `producer` None reads the spec's own."""
    names = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "specs").glob(f"{spec_id}-*.md"))
    if producer is None:
        producer = producer_for(spec_id)
    if valid_approval_for(commits, producer=producer, spec_id=spec_id):
        return True
    return bool(names) and all(valid_approval_for(commits, path=n, producer=producer) for n in names)


def approval_refusal(a, commits, now, path=None, producer=None, spec_id=None):
    """Why one parsed approval record cannot count, or None when it does. THE ONE approval predicate:
    the push check (valid_approval_for) and the daily summary (landed_summary) both judge through it.
    Valid: approved, scope an object bound to a commit of `commits`, unexpired at `now`, scoping `path`
    and naming `spec_id` when given, and (VELDO-0272 N2, FAIL CLOSED) an approver who names somebody.
    With `producer` not None the self-approval test always runs: a producer that names nobody (it cannot
    be determined) refuses every approval, and an approver sharing a normalized identity with the
    producer (case, spacing, a mapping or a list) is a self-approval. None means the caller asks no
    self-separation; every call in main() passes one."""
    if not isinstance(a, dict):
        # A payload that PARSES but is not an object is skipped like one that does not parse at all:
        # `"text"` and `[1,2]` are both valid JSON and neither is an approval.
        return "not an object"
    if a.get("decision") != "approved":
        return "not approved"
    # SCOPE MAY NOT BE AN OBJECT, and this is not hypothetical. `proof/WARP-0620/
    # approval-dmitry.json` predates the current shape: it declares the same
    # `veldo.approval/v1` schema but carries PROSE in `scope` and its `spec_id` at the top
    # level. Two incompatible shapes under one schema string is the actual defect; the record
    # itself is a faithful account of a decision Dmitry made and is not going to be rewritten
    # to suit a parser.
    #
    # An approval whose scope is not an object cannot be commit-bound, and validity REQUIRES
    # commit binding, so skipping is the same answer the next line gives when `bound` is missing.
    scope = a.get("scope")
    if not isinstance(scope, dict):
        return "scope is not an object"
    bound = scope.get("commit")
    if not isinstance(bound, str) or not bound or not any(c.startswith(bound) for c in commits):
        return "not bound to a commit of the push"
    try:
        exp = datetime.datetime.fromisoformat(a["expires_at"].replace("Z", "+00:00"))
        if exp <= now:
            return "expired"
    except Exception:
        return "no readable expiry"
    if path is not None and not _approval_covers(a, path):
        return "scope does not cover %s" % path
    if spec_id is not None and scope.get("spec_id") != spec_id:
        return "scope does not name %s" % spec_id
    if not _identities(a.get("approver")):
        return "names no approver"
    if producer is not None:
        if not _identities(producer):
            return "the producer cannot be determined"
        if _identities(a.get("approver")) & _identities(producer):
            return "self-approval"
    return None


def valid_approval_for(commits, path=None, producer=None, spec_id=None, accept=None):
    """An approval is valid if it is approved, unexpired, commit-bound to a
    commit in the push range, and - when a path is given - scopes that path.
    Commit binding to HEAD alone is unsatisfiable (the approval lands in an
    evidence commit that cannot name its own hash), so range binding is used.
    Self-separation: an approver who is also the proof producer cannot approve
    their own work, and (VELDO-0272 N2) an approval naming no approver, or one
    judged against a producer that cannot be determined, is refused (see
    approval_refusal, the one predicate). `accept`, when given, is a caller's
    own scope test on the approval object (the nightly sweep's run id and
    cases, VELDO-0267): it narrows which approvals count and never replaces a
    check above."""
    if isinstance(commits, str):
        commits = [commits]
    now = datetime.datetime.now(datetime.timezone.utc)
    for f in _corpus_files(_VC.APPROVAL_PATTERN):
        try:
            a = json.loads(f.read_text())
        except Exception:
            continue
        refusal = approval_refusal(a, commits, now, path=path, producer=producer, spec_id=spec_id)
        if refusal is not None and refusal != "self-approval":
            continue
        if accept is not None and not accept(a):
            continue
        if refusal == "self-approval":
            continue  # self-approval: the approver produced the work
        return str(f)
    return None


def push_producer(spec_ids):
    """The producers of the specs a push lands, as one list for the self-approval test, or "" when it
    cannot be determined (VELDO-0272 N2): no landing spec, or one whose proof records no producer. Never
    the producer of whatever verdict happens to bind HEAD or its parent, which is "" after one trailing
    commit and switched the test off."""
    producers = [producer_for(sid) for sid in spec_ids]
    if not producers or any(not _identities(p) for p in producers):
        return ""
    return producers


def _status_at(rev, sid, cache):
    """The status in spec `sid`'s front matter at `rev`, "absent" (no spec file of that id) or
    "unreadable" (Git cannot read it, more than one file carries the id, or no front matter)."""
    by_id = _spec_names(rev, cache)
    names = None if by_id is None else by_id.get(sid, [])
    if names == []:
        return "absent"
    if not names or len(names) != 1:
        return "unreadable"
    r = _git_process.run(["git", "show", "%s:%s" % (rev, names[0])], capture_output=True, cwd=ROOT)
    try:
        fm = _Y.front_matter(r.stdout.decode("utf-8"), names[0]) if r.returncode == 0 else None
    except Exception:
        fm = None
    return str(fm.get("status")) if isinstance(fm, dict) else "unreadable"


def _built_at(rev):
    """The spec ids with a proof bundle file other than an approval record in the tree of `rev`, or None
    when Git cannot list it."""
    r = _git_process.run(["git", "ls-tree", "-r", "--name-only", rev, "proof/"], capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        return None
    return {m.group(1) for m in (_PROOF_FILE.match(f) for f in r.stdout.splitlines() if not _approval_record(f)) if m}


def on_base(files):
    """VELDO-0287: the specs a push carries that are already on main: not a draft at the push base
    (push_range, the protected ref's tip) and readable there. They land nothing; a file of theirs the push
    changes is work, which a reviewed landing spec must cover (N3). Absent, draft or unreadable at the
    base, a spec is not on the base. A spec ready on main with no proof bundle there, whose bundle this
    push creates, is its first build (the factory makes a spec ready on main before a worker builds it)
    and lands; one whose bundle is already on main is a re-land and stays on the base (fail closed)."""
    ids = push_specs(files)
    if not ids:
        return set()
    _commits, bases = push_range()
    cache, built = {}, {}

    def first_build(sid):
        if not bundle_touched(sid, files):
            return False
        for b in bases:
            if b not in built:
                built[b] = _built_at(b)
            if built[b] is None or sid in built[b]:
                return False
        return True

    return {sid for sid in ids if bases and all(
        _status_at(b, sid, cache) not in ("absent", "draft", "unreadable") for b in bases) and not first_build(sid)}


def bundle_touched(sid, files):
    """True when the push changes a file of spec `sid`'s proof bundle other than an approval record:
    the spec was built in this push (VELDO-0287)."""
    return any(_PROOF_FILE.match(f) and _PROOF_FILE.match(f).group(1) == sid and not _approval_record(f)
               for f in files)


def built_specs(files):
    """The landing specs whose proof bundle the push changes (VELDO-0287). Only they give the producer and
    need the review; a landing spec with nothing built is judged as a spec-only push judges it."""
    return [sid for sid in landing_specs(files) if bundle_touched(sid, files)]


def landing_specs(files):
    """The specs a push lands: each spec it carries (push_specs) that is new to main (VELDO-0287: not on
    the push base, see on_base) and is not a draft at HEAD. A draft lands no work; an unreadable spec is
    not a draft."""
    out = []
    landed = on_base(files)
    for sid in push_specs(files):
        if sid in landed:
            continue
        try:
            fm = _spec_file_fm(sid)
        except ValueError:
            fm = {}
        if fm.get("status") != "draft":
            out.append(sid)
    return out


def open_emergency_debt():
    ev = ROOT / ".veldo" / "events.jsonl"
    if not ev.exists():
        return None
    open_debts = []
    for line in ev.read_text().splitlines():
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("type") == "emergency.push":
            open_debts.append(e)
        elif e.get("type") in ("emergency.closed", "spec.shipped") and open_debts:
            # a shipped backfill (or explicit close) after an emergency closes the oldest debt
            open_debts.pop(0)
    return open_debts[0] if open_debts else None


def blocking_findings(v):
    """Verdict findings come in two canonical shapes: a dict
    {blocking: [...], non_blocking: [...]} or a list of {severity, text}
    with severity blocking|note. Returns the blocking entries. Anything
    outside both shapes counts as blocking: an unreadable finding must
    fail closed, never slip through."""
    f = v.get("findings")
    if f is None:
        return []
    if isinstance(f, dict):
        b = f.get("blocking")
        if b is None:
            return []
        return list(b) if isinstance(b, list) else [b]
    if isinstance(f, list):
        out = []
        for item in f:
            if isinstance(item, dict) and item.get("severity") in ("note", "non_blocking"):
                continue
            out.append(item)
        return out
    return [f]


def unresolved_blocking(commits):
    """THE NEWEST VERDICT PER SPEC IN THE PUSH RANGE, when it carries blocking findings.
    Returns [(spec_id, path, finding), ...], empty when nothing objects.

    WHAT THIS IS AND IS NOT (WARP-0732). It is NOT a forgery defense and must never be
    described as one. An agent that can write this repository can also delete an inconvenient
    verdict file, and WARP-0730 conceded that fight deliberately after nine rounds established
    that a predicate inside the agent's own process cannot win it. What this buys is narrower
    and real: HONEST work does not merge past an outstanding objection, and evading it now takes
    an affirmative destructive act that shows up in the diff rather than the mere absence of a
    file.

    WHY THIS IS SAFE WHERE REQUIRING A PASS WAS NOT, and the whole design rests on it. Requiring
    a pass verdict is forgeable in the DANGEROUS direction: the agent mints its own approval.
    Objecting is forgeable only in the SAFE direction: a forged finding blocks the forger, which
    no attacker wants. And a forged CLEAN verdict clearing an objection gains nothing either,
    because NO VERDICT IS REQUIRED - never writing the objection reaches the same place with
    less work. A rule may safely admit a forgery that buys the forger nothing.

    NEWEST WINS, BY COMMIT ORDER, because the push range holds the branch's own earlier
    candidate commits: a REWORK on the commit before the fix must not block the fix forever.
    Two verdicts on the SAME commit fail closed and blocking wins. So does a findings shape the
    parser does not recognise, which is blocking_findings' own rule and is not weakened here."""
    order = {c: i for i, c in enumerate(commits)}          # 0 is newest (HEAD first)
    newest = {}
    for f in _verdict_files():
        try:
            v = json.loads(f.read_text())
        except Exception:
            continue
        c = v.get("commit") or ""
        rank = next((order[full] for full in order if c and full.startswith(c)), None)
        if rank is None:
            continue
        sid = v.get("spec_id") or ""
        prev = newest.get(sid)
        # same commit -> the objecting verdict wins, so a clean twin cannot clear it
        if prev is None or rank < prev[0] or (rank == prev[0] and blocking_findings(v)):
            newest[sid] = (rank, f, v)
    out = []
    for sid, (_rank, f, v) in sorted(newest.items()):
        for finding in blocking_findings(v):
            out.append((sid, f, finding))
    return out


def proof_digest(manifest):
    """Stable digest of a proof manifest's substance (spec, criteria, checks),
    so a verdict can bind to the exact proof it reviewed. Identical to the
    copy in validate.py; selftest asserts they do not drift."""
    payload = {
        "spec_id": manifest.get("spec_id"),
        "commit": manifest.get("commit"),
        "criteria": manifest.get("criteria"),
        "checks": manifest.get("checks"),
    }
    blob = json.dumps(payload, sort_keys=True, default=str)
    return "sha256:" + hashlib.sha256(blob.encode()).hexdigest()[:16]


def _proof_for_spec(spec_id):
    for p in _corpus_files(_VC.MANIFEST_PATTERN):
        if p.parent.name != spec_id:
            continue
        try:
            return p, json.loads(p.read_text())
        except Exception:
            return p, None
    return None, None


def producer_for(spec_id):
    _, m = _proof_for_spec(spec_id)
    return (m or {}).get("producer", "")


def _spec_file_fm(spec_id):
    for p in sorted((ROOT / "specs").glob(f"{spec_id}*.md")):
        fm = _Y.front_matter(p.read_text(), str(p))
        if fm is None:
            raise ValueError(f"{p}: no YAML front matter")
        return fm
    return {}


def ready_boundary_violations():
    """A spec that has a proof manifest must not still be a draft: proof of a
    draft is a boundary someone crossed without the spec being ready."""
    bad = []
    for p in _corpus_files(_VC.MANIFEST_PATTERN):
        try:
            m = json.loads(p.read_text())
        except Exception:
            continue
        sid = m.get("spec_id")
        if not sid:
            continue
        fm = _spec_file_fm(sid)
        if fm.get("status") == "draft":
            bad.append(sid)
    return bad


_COMMIT = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")


def _spec_at(commit, spec_id):
    """(the spec document's exact bytes, its front matter) as committed at `commit`, or None when
    that cannot be named for certain: an object id that is not a full commit id, no spec file of
    that id at the commit, more than one, or a Git refusal."""
    if not isinstance(commit, str) or not _COMMIT.fullmatch(commit):
        return None
    r = _git_process.run(["git", "ls-tree", "--name-only", commit, "specs/"],
                         capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        return None
    names = [n for n in r.stdout.splitlines() if n.startswith("specs/%s-" % spec_id) and n.endswith(".md")]
    if len(names) != 1:
        return None
    b = _git_process.run(["git", "show", "%s:%s" % (commit, names[0])], capture_output=True, cwd=ROOT)
    if b.returncode != 0:
        return None
    try:
        fm = _Y.front_matter(b.stdout.decode("utf-8"), names[0])
    except Exception:
        return None
    if not isinstance(fm, dict):
        # No readable front matter is a shape this check cannot name for certain: stale, never current.
        return None
    return b.stdout, fm


def _digest_revision_stale(sid, pr, commit, current):
    """VELDO-0137: a VELDO-0050 proof names its accepted revision as 'sha256:' and the digest of the
    exact spec bytes it was accepted against (control_proof.digest). It is current when the spec
    committed at the proof's own implementation commit is exactly those bytes (VELDO-0050 refuses a
    build that changes its spec, so that is the accepted revision) and the spec's declared revision
    has not been raised since. A later edit that raises nothing, such as a History line at landing,
    leaves it current. Anything that cannot be named for certain is stale: fail closed."""
    then = _spec_at(commit, sid)
    if then is None or "sha256:" + hashlib.sha256(then[0]).hexdigest() != pr:
        return True
    try:
        return int(current.get("revision", 1)) > int(then[1].get("revision", 1))
    except (ValueError, TypeError):
        return True


def spec_revision_stale():
    """If a spec declares a revision higher than the revision its proof was
    produced against, the proof is stale and must be re-run. A VELDO-0050 proof's
    digest-form revision is judged by _digest_revision_stale."""
    stale = []
    for p in _corpus_files(_VC.MANIFEST_PATTERN):
        try:
            m = json.loads(p.read_text())
        except Exception:
            continue
        sid = m.get("spec_id")
        pr = m.get("spec_revision")
        if not sid or pr is None:
            continue
        fm = _spec_file_fm(sid)
        if isinstance(pr, str) and pr.startswith("sha256:"):
            if _digest_revision_stale(sid, pr, m.get("commit"), fm):
                stale.append(sid)
            continue
        try:
            if int(fm.get("revision", 1)) > int(pr):
                stale.append(sid)
        except (ValueError, TypeError):
            stale.append(sid)
    return stale


def valid_verdict_for(commit, spec_id=None, bound=False, producer=None):
    """A passing verdict bound to `commit`. VELDO-0272: `spec_id` narrows it to one spec, `bound`
    requires a proof digest (an unbound verdict reviewed no particular proof), and a `producer` (not
    None) refuses a verdict with no reviewer, a verdict whose reviewer shares a normalized identity with
    that producer, and every verdict when the producer is empty (no self-review, fail closed)."""
    for f in _verdict_files():
        try:
            v = json.loads(f.read_text())
        except Exception:
            continue
        if not isinstance(v, dict) or not isinstance(v.get("commit", "\0"), str):
            continue
        if v.get("verdict") in ("pass", "pass_with_notes") and commit.startswith(v.get("commit", "\0") or "\0"):
            if blocking_findings(v):
                continue
            if spec_id is not None and v.get("spec_id") != spec_id:
                continue
            if producer is not None and _self_review(v.get("reviewer"), producer):
                continue
            # if the verdict binds to a proof digest, it must match the current
            # proof manifest for that spec - a verdict cannot be reused for a
            # proof it did not review.
            pd = v.get("proof_digest")
            if bound and not pd:
                continue
            if pd:
                sid = v.get("spec_id")
                _, m = _proof_for_spec(sid) if sid else (None, None)
                if not m or proof_digest(m) != pd:
                    continue
            return str(f)
    return None


def _head_spec_id():
    """The spec id of the change at HEAD, via the verdict bound to HEAD or its
    parent (the evidence-commit case)."""
    h = head()
    parent = _git_process.run(["git", "rev-parse", "HEAD^"], capture_output=True,
                            text=True, cwd=ROOT).stdout.strip()
    for f in _verdict_files():
        try:
            v = json.loads(f.read_text())
        except Exception:
            continue
        c = v.get("commit", "")
        if c and (h.startswith(c) or (parent and parent.startswith(c))):
            return v.get("spec_id")
    return None


# THE NIGHTLY SWEEP (VELDO-0267). While the latest finished nightly mutation sweep on the trunk is
# red, landing is refused as nightly_red, until a later sweep is green or the owner's approval
# (veldo.approval/v1) names that sweep's run id and every failing case with a reason. It applies to
# the landing check only: the lander's installed policy run (BASE set) and a run told it judges a
# protected ref (--protected-ref, or LANDING set by a caller that knows the destination). A working
# branch's push and a candidate's own gate are never refused by it. The sweep records are read from
# the state directory the INSTALLATION's scripts/mutation_selection.json names, outside every
# candidate tree, with the installation's own reader; an installation without that reader (every
# adopter's) has no nightly sweep and nothing to refuse.
LANDING = None
# The loader helper that loads a file from outside every installed directory by design (the
# installation's own scripts/mutation_selection.py, which an adopter's installation lacks), declared
# so the authority service's closure reads it as no module of the fixed executable (VELDO-0148's form).
EXTERNAL_LOADERS = ("_installation_module",)


def _installation_module(alias, path):
    spec = importlib.util.spec_from_file_location(alias, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _nightly_reader():
    reader = Path(__file__).resolve().parent.parent / "scripts" / "mutation_selection.py"
    if not reader.is_file():
        return None
    return _installation_module("veldo_mutation_selection", reader)


def approval_rule():
    """The protected-path approval rule over this push, for a caller that adds its own scope test:
    accept -> the approval file valid_approval_for finds (approved, unexpired, bound to a commit of
    the push range, approver not the work's producer, and accepted by `accept`), or None. The
    nightly check (VELDO-0267) explains a red sweep only through it, never through a second copy."""
    commits = push_range_commits() or [head()]
    files = changed_files()
    producer = approval_producer(push_producer(built_specs(files)), files, commits)
    return lambda accept: valid_approval_for(commits, producer=producer, accept=accept)


def nightly_refusal():
    """None, or the line that refuses landing as nightly_red."""
    reader = _nightly_reader()
    if reader is None:
        return None
    try:
        state = reader.state_directory(reader.load_rule(reader.RULE))
    except reader.Invalid as error:
        return "nightly_red: the nightly sweep state cannot be located (%s)" % error
    try:
        rule = approval_rule()
    except Exception:  # The push range cannot be read: no approval explains anything.
        rule = None
    refused = reader.landing_refusal(state, rule)
    return None if refused is None else "%s: %s" % refused


def main():
    h = head()

    # NO VERDICT IS REQUIRED HERE ANY MORE (WARP-0730). A verdict is an artifact the agent
    # can write, so requiring one asked an agent to certify itself, and nine build rounds were
    # spent trying to stop it forging that certificate. A predicate inside the agent's own
    # process cannot win that fight: it has the filesystem, the repository and the interpreter,
    # and every round closed one spelling while the next opened another.
    # So the authority moved instead of being defended. For ordinary work the GATE decides -
    # a green scripts/verify.sh is done, and it is not something an agent can forge into
    # existence. For protected paths the OWNER decides, enforced by the approval block below,
    # which is unchanged and is the one thing here an agent genuinely cannot produce.
    # valid_verdict_for() is deliberately KEPT and simply no longer consulted at this gate:
    # reviews still run and still report findings for a human to read, they just no longer
    # certify. Deleting the machinery is a separate item, so that a regression in either change
    # can be attributed to the change that caused it.
    # VELDO-0272 (owner, 2026-11-07, Telegram 39707 and 39708) consults it again, for one case only:
    # the owner left the approval of routine work, so a push whose specs are all not_required and
    # that touches no protected path lands on a recorded review by someone who is not the producer.
    # The forgery limit above still holds and the merge rule states it: the reviewer identity check
    # and the daily summary make a forged review visible, not impossible.
    #
    # BUT AN OBJECTION STILL STOPS THE PUSH (WARP-0732), and leaving that out was a real gap
    # rather than a consequence of the above. Dmitry, 2026-08-02: "Not good if werdict is rework
    # still would merge. That's fluff and real theater." Requiring a PASS is forgeable in the
    # dangerous direction and stays gone; blocking on a recorded OBJECTION is forgeable only in
    # the safe direction, because a forged finding blocks the forger. See unresolved_blocking.
    rng_f = push_range_commits() or [h]
    objections = unresolved_blocking(rng_f)
    if objections:
        # THE OWNER'S OVERRIDE IS THE APPROVAL BLOCK THAT ALREADY EXISTS, not a new artifact and
        # not a new field: it is the one thing at this gate an agent cannot produce, and an
        # override belongs on that footing. Self-approval is refused by valid_approval_for.
        files_f = changed_files()
        override = valid_approval_for(rng_f, producer=approval_producer(push_producer(built_specs(files_f)), files_f, rng_f))
        if not override:
            print("VELDO policy: blocked. A review objected and the objection is unresolved.")
            for sid, path, finding in objections:
                try:
                    rel = path.relative_to(ROOT)
                except Exception:
                    rel = path
                print(f"  {sid}: {rel}")
                print(f"    {str(finding)[:300]}")
            print("  Resolve it the normal way: fix the work, commit, and let the re-review land")
            print("  a verdict on the newer commit. A review can object but never approve, so no")
            print("  pass verdict is required and none will clear this.")
            print("  To override, record an approval bound to a commit in this push, approved by")
            print("  someone who is not the proof producer.")
            return 1
        print("VELDO policy: review objection OVERRIDDEN by recorded owner approval "
              f"({len(objections)} finding(s)).")

    # protected paths -> commit-bound, unexpired approval required
    pats = protected_patterns()
    touched = []
    for f in changed_files():
        for p in pats:
            if glob_covers(f, p):
                touched.append((f, p))
                break
    if touched:
        rng = push_range_commits() or [h]
        # each touched protected path needs an approval that names it, whose
        # approver is not the work's producer (self-separation).
        files_p = changed_files()
        producer = approval_producer(push_producer(built_specs(files_p)), files_p, rng)
        for tf, p in touched:
            if not valid_approval_for(rng, path=tf, producer=producer):
                print("VELDO policy: blocked. Protected path touched with no valid path-scoped approval.")
                print(f"  {tf}  (protected by {p})")
                print("  Required: an approved, unexpired veldo.approval/v1 whose scope.commit is a")
                print(f"  commit in this push, whose scope.paths covers {tf}, and whose approver")
                print("  is not the proof producer (no self-approval)%s." % (
                    "" if producer else "; the producer cannot be determined (no landing spec, or one whose"
                    " proof records no producer), so every approval is refused"))
                return 1

    # VELDO-0272 AC3 (a): nothing lowers a flag silently. A lowering of a spec's human_approval from
    # required, between the push base and HEAD or in any commit of the push (by spec id, merges and
    # renames included, an unreadable earlier value counting as required), needs an owner approval
    # scoping every file the spec had on both sides.
    rng, bases = push_range()
    if not rng:
        rng, bases = [h], _parents(h)
    pushed = changed_files()
    for sid, c, files in lowered_flags(rng, bases):
        producer = approval_producer(producer_for(sid), pushed, rng)
        missing = [f for f in files if not valid_approval_for(rng, path=f, producer=producer)] if files else ["specs/%s-*.md" % sid]
        if missing:
            print("VELDO policy: blocked. approval_flag_lowered: %s" % ", ".join(files or missing))
            print(f"  commit {c[:12]} lowers {sid}'s human_approval from required (or from a value that")
            print("  cannot be read), and no approved, unexpired veldo.approval/v1 bound to a commit in this")
            print(f"  push, whose scope.paths covers {', '.join(missing)} and whose approver is not the")
            print("  proof producer, records the owner's decision to lower it.")
            return 1

    # VELDO-0272 AC3 (b), judged PER SPEC (the reading recorded in the spec's History, check F5): every
    # spec this push carries needs a passing verdict bound to a commit in the push and to the spec's
    # current proof digest, from a reviewer who is not the producer, whatever else the push carries; a
    # spec the rule computes as required needs the owner's approval as well, never instead.
    # Fix round 5: a push that changes only spec files, derived projections and approval records lands no
    # work, so no review of it can exist yet (a spec moved from draft to ready, a re-mark). It is judged
    # only for the specs whose files it changes, and only for the owner's approval their flag requires.
    only_specs = spec_only(pushed)
    carried = sorted({m.group(1) for m in (_SPEC_FILE.match(f) for f in pushed) if m}) if only_specs else landing_specs(pushed)
    for sid in carried:
        try:
            fm = _spec_file_fm(sid)
        except ValueError:
            fm = {}
        if fm.get("status") == "draft":
            # A draft lands no work: it cannot carry proof (the ready boundary below refuses one), so
            # no verdict can bind to it. It covers no work either: the N3 check below refuses a push
            # changing anything but spec files and proof bundles with only drafts; an unreadable spec is not a
            # draft and is judged.
            continue
        # VELDO-0287 (c): a landing spec whose proof bundle the push does not change (ready, nothing
        # built) is judged as a spec-only push judges it: the owner approval its flag requires, no review.
        if only_specs or not bundle_touched(sid, pushed):
            if effective_flag(fm, pats) == "required" and not owner_approved(
                    sid, rng, producer=approval_producer(producer_for(sid), [f for f in pushed if _SPEC_FILE.match(f)], rng)):
                bases_ = approval_bases(fm, pats) or ["declared required"]
                print("VELDO policy: blocked. owner approval missing: %s is approval required (%s)" % (sid, "; ".join(bases_)))
                print("  Required (a push changing only spec files): an approved, unexpired veldo.approval/v1 bound to")
                print("  a commit in this push, whose scope names this spec, and whose approver is not a committer of")
                print("  the push when the spec has no proof producer.")
                return 1
            continue
        if not reviewed_landing(sid, rng):
            print("VELDO policy: blocked. landing_without_review: %s" % sid)
            producer = producer_for(sid)
            print("  Required: a pass or pass_with_notes verdict with no blocking findings, bound")
            print("  to a commit in this push and to the spec's current proof digest, whose")
            print("  reviewer is not the proof producer (%s)." % (producer or "no producer recorded: refused"))
            return 1
        if effective_flag(fm, pats) == "required" and not owner_approved(sid, rng):
            bases_ = approval_bases(fm, pats) or ["declared required"]
            print("VELDO policy: blocked. owner approval missing: %s is approval required (%s)" % (sid, "; ".join(bases_)))
            print("  Required: an approved, unexpired veldo.approval/v1 bound to a commit in this push,")
            print("  whose scope names this spec (scope.spec_id, or scope.paths covering its spec file)")
            print("  and whose approver is not the proof producer.")
            return 1

    # VELDO-0272 N3: a push that changes anything but spec files and proof bundles must be covered by a spec
    # whose landing the loop above judged (reviewed, and owner approved when required). A draft spec
    # covers nothing, and neither does a ready spec switched back to draft in the same push: it is a
    # draft at HEAD. Without this, code with no spec, or with only a draft beside it, landed unreviewed.
    # A spec file, a file of a spec's proof bundle, a derived projection or an approval record is exempt;
    # any other file under specs/ or proof/ (a script, a loose note) is work like any other (VELDO-0272 fix
    # rounds 4 and 5).
    # VELDO-0287 (b): a spec file or bundle file of a spec already on main is work, in any push that is
    # not spec-only; only a landing spec this push built (and so reviewed above) covers work.
    landed = set() if only_specs else on_base(pushed)
    work = sorted(f for f in pushed if not _not_work(f)) + sorted(
        f for f in pushed if (_SPEC_FILE.match(f) or _PROOF_FILE.match(f)) and not _approval_record(f)
        and (_SPEC_FILE.match(f) or _PROOF_FILE.match(f)).group(1) in landed)
    if work and not built_specs(pushed):
        print("VELDO policy: blocked. landing_without_review: no spec covers %s" % ", ".join(work[:5])
              + (" (and %d more)" % (len(work) - 5) if len(work) > 5 else ""))
        print("  A push that changes anything but spec files and proof bundles must carry a spec that is not a")
        print("  draft at HEAD, with a pass or pass_with_notes verdict bound to a commit in this push and")
        print("  to its current proof digest, from a reviewer who is not the proof producer (and the")
        print("  owner's approval when the spec is approval required). A draft spec covers nothing.")
        return 1

    # ready-spec boundary: no draft spec may carry a proof
    drafts = ready_boundary_violations()
    if drafts:
        print("VELDO policy: blocked. A draft spec has a proof manifest (ready-boundary): "
              + ", ".join(drafts))
        print("  A spec must be ready before it is built and proven; promote it or remove the proof.")
        return 1

    # spec-revision invalidation: a proof older than its spec's revision is stale
    stale = spec_revision_stale()
    if stale:
        print("VELDO policy: blocked. Proof is stale versus its spec revision: "
              + ", ".join(stale))
        print("  The spec revised after the proof ran; re-run the gate, proof, and review.")
        return 1

    # a red nightly sweep blocks landing only (VELDO-0267)
    if BASE is not None or LANDING or "--protected-ref" in sys.argv[1:]:
        refused = nightly_refusal()
        if refused:
            print("VELDO policy: blocked. " + refused)
            print("  The latest nightly mutation sweep on the trunk is red. Landing waits until a later")
            print("  sweep is green, or the owner's approval (veldo.approval/v1) names that sweep's run id")
            print("  in scope.nightly_run and every failing case with a reason in scope.cases.")
            return 1

    # emergency debt blocks ordinary pushes
    debt = open_emergency_debt()
    if debt:
        print("VELDO policy: blocked. An emergency backfill debt is open "
              f"(emergency.push at {debt.get('at')}, commit {debt.get('commit','')[:12]}).")
        print("  Land the backfill (spec + proof + review) or record an emergency.closed event; "
              "the setup's promise is that unclosed debt blocks the next ordinary merge.")
        return 1

    return 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["--protected-ref"]:
        sys.exit(_protected_ref_main(sys.argv[2:]))
    # A range, base or parent Git cannot read (VELDO-0272's push_range, outside a repository or on an
    # unreadable history) refuses as a stated block with the same exit 1, never a traceback (landing-c).
    try:
        code = main()
    except RuntimeError as error:
        print("VELDO policy: blocked. %s; nothing can be judged, so the push is refused." % error)
        code = 1
    sys.exit(code)
