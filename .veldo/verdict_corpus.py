#!/usr/bin/env python3
"""THE ONE ENUMERATION OF THE PROOF CORPUS: one membership rule, two path sources, ONE ANCHORING.

WHY THIS MODULE EXISTS, AS A LAW AND NOT AS A BUG REPORT. When two mechanisms compute
what is claimed to be the same set, the GAP BETWEEN THEM is an attack surface and
NEITHER MECHANISM CAN SEE IT. Each side is individually correct and individually tested;
the defect lives only in the difference, so no test of either side can find it. `*`, `**`,
case folding, symlink following, unicode normalisation, path quoting, dotfile handling AND
THE DIRECTORY A PATHSPEC IS ANCHORED AT all differ between git, pathlib, shell and regex, and
every one of those differences is a new spelling of the same defect.

THE DEFECT THIS CLOSES, MEASURED AT ffaab41 BEFORE ANY CHANGE. The projection's
entitlement domain was `git ls-files 'proof/*/verdict*.json'`, and the contract validator's
corpus was `Path('proof').glob('*/verdict*.json')`. A GIT PATHSPEC `*` CROSSES `/`; A
PATHLIB `*` DOES NOT. So a verdict-shaped file committed at `proof/<a>/<b>/verdict.json`,
two directories deep instead of one, was simultaneously INSIDE the entitlement domain and
INVISIBLE to the validator. With file contents literally `{"schema": "nope", "verdict":
"pass"}`: `python3 .veldo/validate.py all` exited 0, then plain `python3 .veldo/events.py
reconcile-verdicts` with NO ARGUMENTS appended a verdict.recorded declaring `"verdict":
"pass"` for it, taking the log md5 from 4b20b0fe19ec to d262da987e54 and reporting
`1 appended`, and `bash scripts/verify.sh` printed GATE: GREEN over the whole thing. THE
GATE WAS THE APPENDER, and an append-only log cannot take that back.

IT WAS NEVER ONE ROUTE. Driven over a battery generated from the vocabulary the two
mechanisms differ on, SIX of nineteen candidate spellings were entitled and never
validated: depth 2, depth 3, depth 2 with a suffixed name, a hidden directory component,
`proof/proof/<id>/verdict.json`, and a file under a directory named `verdict.json.d`. And
the divergence ran the OTHER WAY TOO, which is worse than the forgery: git quotes a
non-ASCII path by default (`core.quotePath`), so a genuine verdict under
`proof/R-NFC-cafe\303\251/` was VALIDATED AND NOT ENTITLED under its real spelling while its
C-quoted spelling was ENTITLED AND NOT VALIDATED - one file diverging in BOTH directions -
and it was not merely dropped: it was APPENDED with the C-quoted string as its spec id, a
permanently corrupt line in an append-only log.

SO PATCHING THE PATHLIB GLOB TO BE RECURSIVE WOULD HAVE FIXED ONE CASE OF A CLASS, and the
next spelling difference reopens it. There is instead exactly ONE membership rule here,
`corpus_member`, and exactly TWO path sources that rule is applied to: the git index and
the working tree. NEITHER SOURCE USES A WILDCARD. The git side asks for a DIRECTORY under
the literal pathspec magic (`:(top,literal)`, so git performs no glob matching whatever and
no `*` semantics are involved at all) and reads it NUL delimited so nothing is quoted; the
disk side walks that same directory. The pattern is DATA passed to one matcher, never a
second pattern kept in step with the first by hand.

AND EXACTLY ONE ANCHORING, WHICH IS THE SECOND HALF OF THE SAME LAW AND WAS MEASURED MISSING
AT bdb4055. That commit shipped TWO pathspecs, a bare `proof` read relative to the caller's
CWD and a `:(top)proof` read relative to the top of the repository, and called them the same
directory. THEY ARE NOT, whenever the VELDO root is not itself the top: with VELDO vendored at
`sub/` of an outer repository, `:(top)proof` names the OUTER `proof` and `proof` names the
vendored one, so a forged `{"schema": "nope", "verdict": "pass"}` committed at the outer
`proof/WARP-9999/verdict.json` was ENTITLED in the vendored VELDO's own log (`1 appended`, log
md5 4dfbb70941b3 -> 512c0e46b306) while `validate.py all` exited 0 both before and after; and
in the same shape the contract check saw an entitlement of 0 against a domain of 166 and
passed, withholding every genuine verdict in that repository forever. The two spellings also
defaulted their GIT CWD to the PROCESS CWD, so the same clone invoked by absolute path from a
directory that is not a repository reported 0 tracked where the code this replaced reported
166, and one report named a path belonging to a FOREIGN repository the caller happened to be
standing in. THE FIX IS STRUCTURAL, not a third pathspec: `corpus_pathspec` resolves the VELDO
ROOT'S OWN PREFIX once, with git's `rev-parse --show-prefix`, and every enumeration below is
read at `:(top,literal)<that prefix>proof` and answers in paths RELATIVE TO THAT ROOT. There
is no cwd-anchored form left to disagree with, no caller that can pass one root to the disk
half and another to the git half, and no default that reaches the process cwd at all: THE
ROOT IS A REQUIRED ARGUMENT of every function here that talks to git.

WHAT THAT BUYS, AND IT IS THE POINT: the two sets can no longer differ BY SPELLING or BY
ANCHORING, whatever the spelling is, because there is one of each. They can still differ by
SOURCE, index versus working tree, and by RULE, if somebody edits the rule. The SOURCE
difference is enumerated in both directions by `divergence` and the gate is RED on it, per
path, with the reason named.

AND THE TRACKED-OR-NOT QUESTION IS PUT TO GIT, NOT TO THE ENUMERATION UNDER TEST, which is the
third half of the same law and was measured missing at 098dc6a. The inverse-harm direction is
excused for exactly one reason - the path is not committed yet - and that reason was computed as
`disk - tracked` from the same reading it was validating, which made the contradiction leg
`(disk - members) intersect tracked` and therefore IDENTICALLY EMPTY FOR EVERY POSSIBLE INPUT: a
guard whose failing case cannot be constructed, sold as coverage of both directions. Untracked-ness
is now `tracked_direct`, a bare `ls-files` at the VELDO root with NO pathspec and NO prefix
arithmetic, so a mangled or misanchored pathspec cannot silence the check that exists to catch it,
and the disagreement is red per path in both directions (`contradiction` and `overclaimed`). What
that costs is one more git read per pattern; what it buys is the only leg here that can fail when
the enumeration is wrong.

THE RULE DIFFERENCE IS NOT CONTAINED BY ANYTHING HERE, and the
sentence that used to say it was has been deleted rather than softened: widening the rule
widens BOTH sides together, so the forged artifact it newly admits becomes one the validator
VALIDATES AND the reconciler APPENDS. Driven: under a widened rule the forged body is
entitled, `validate.py` exits 1 naming it, AND `reconcile-verdicts` writes the event anyway,
because the gate runs the reconciler AFTER the contract stage and does not gate the append on
it. A WIDENING ADMITS AN APPENDABLE FORGERY. What widening cannot do is reopen the SPELLING
gap, which is the class this module closes; a narrowing is named by `misfiled`.

WHAT THIS DOES NOT REACH, DECLARED AS LIMITS AND NOT DEFENDED AGAINST:
  * THE TWO SETS ARE ONE ENUMERATION OF PATHS AND NOT OF CONTENT, WHICH IS THE SAME CLASS ONE AXIS
    DOWN. Everything above makes the domain and the validated set agree about WHICH PATHS are
    corpus members. NOTHING HERE COMPARES THEIR BYTES: the contract validator reads the WORKING
    TREE through `disk_corpus`, `committed_blobs` keys the INDEX blob, and no check asks whether the
    bytes keyed are the bytes read. Measured at 2f6cc25: commit a forged `{"schema": "nope",
    "verdict": "pass"}` over a tracked corpus path and leave the genuine bytes in the working tree
    UNSTAGED, so the index equals HEAD and the path is on disk - neither exclusion below fires.
    `validate.py all` exits 0 with ZERO output lines, and plain `reconcile-verdicts` appends a
    verdict.recorded declaring `"verdict": "pass"` and carrying verdict_blob
    81fe14a7e5d150ec93346636727c0090b33c16a8, log md5 3ce08ca1f477 -> 8937421a420a, whose bytes are
    the forgery and which no validator ever read (`git hash-object` of the working-tree file is
    2699a63397c6d420, a different object). IDENTICAL at ffaab41 (log md5 4b20b0fe19ec ->
    01efc9b1adb9), so it is PRE-EXISTING and not a regression of this item; the blob is the same in
    both columns because a blob sha is a property of content. KNOWN OPEN, spec WARP-0728: the keyed
    bytes and the validated bytes must be the same bytes.
  * A CORPUS-SHAPED FORGERY IS STILL APPENDED. A file at `proof/<id>/verdict.json` whose body
    is `{"schema": "nope", "verdict": "pass"}` IS a corpus member by shape, so it is entitled;
    `validate.py all` exits 1 naming it, and plain `reconcile-verdicts` appends it anyway
    (measured at bdb4055, log md5 4dfbb70941b3 -> 304d580fded5). This item changed the GATE
    COLOUR for that case and NOT the append, because the gate's reconciler stage is not
    conditioned on the contract stage. Pre-existing, not a regression, and open: gating the
    append on a green contract stage is a separate item.
  * ENTITLEMENT IS KEYED ON THE LOG'S PATH SPELLING, NOT ON THE IDENTITY OF THE FILE
    ACTUALLY OPENED. `events.log_entitlement` resolves a repository from the log's own
    location while the bytes are written by `open(log, "a+")`, which follows the final
    component, so symlinking or hardlinking an attacker's log at the victim's name transfers
    entitlement. KNOWN OPEN, a separate item, and nothing here closes it.
  * A writer that never imports this module (a shell append, a hand-edited log) and
    arbitrary in-process Python. Both can already append directly; that is the signed-log
    question, not this one.
  * A process environment that redirects what git ANSWERS. Measured on the module this
    replaces: GIT_DIR and GIT_WORK_TREE pointed at an attacker's repository make that
    repository's enumeration the domain.
"""
import fnmatch
import os
import subprocess
from pathlib import Path, PurePosixPath

# THE DECLARED PROOF ROOT, and the corpus patterns as DATA. Each pattern is a filename
# glob applied to the FINAL COMPONENT ONLY by the one matcher below. They are not path
# patterns and are never handed to git or to pathlib, which is what keeps their meaning
# independent of whose glob implementation is reading them.
PROOF_ROOT = "proof"
VERDICT_PATTERN = "verdict*.json"
DESIGN_VERDICT_PATTERN = "design-verdict*.json"
APPROVAL_PATTERN = "approval*.json"
MANIFEST_PATTERN = "manifest.json"

# THE PATHSPEC MAGIC THAT MAKES THE ONE ANCHORING ONE. `:(top)` fixes the pathspec to the
# repository rather than to whatever directory the caller happens to be standing in, and
# `:(literal)` tells git that no character in what follows is a wildcard - so a proof root, or
# a VELDO root prefix, containing `*`, `?` or `[` cannot acquire glob semantics on the git side
# that the disk side does not have. Together they are what leaves NO `*` anywhere in this
# module's conversation with git.
CORPUS_PATHSPEC_MAGIC = ":(top,literal)"

# The engine directory a VELDO root keeps its modules and its event log in. Spelled ONCE, here,
# because the root a log is resolved back to and the root the pathspec is anchored at have to be
# the same directory or the anchoring is anchored to nothing.
VELDO_DIR = ".veldo"

# The index modes of a REGULAR FILE. `git ls-files -s` also reports a symlink (120000) and a
# gitlink (160000), and both carry a 40 hex object name that looks exactly like a blob: a tracked
# symlink at a corpus path would key an event whose recorded verdict, round and commit are all
# absent. Only a regular file is an artifact; anything else is excluded with the mode named.
INDEX_FILE_MODES = ("100644", "100755")
_OBJECT_NAME_LEN = 40
_HEX = set("0123456789abcdef")


def _posix(rel):
    """One repository relative path in ONE spelling. Everything below compares strings, so
    the normalisation has to happen in exactly one place or the comparison is the next
    divergence."""
    return PurePosixPath(str(rel).replace(os.sep, "/")).as_posix()


def corpus_member(rel, pattern):
    """THE ONE MEMBERSHIP RULE. A corpus artifact is a path of EXACTLY three components,
    `<proof root>/<one directory>/<name>`, whose name matches the pattern.

    Both the entitlement domain and the validated set are this predicate applied to a
    source of paths, so they cannot disagree about what a corpus path IS. The structure is
    counted, not matched, because a count cannot be spelled two ways. The name test is
    `fnmatch.fnmatchcase`: CASE SENSITIVE on every platform, unlike `fnmatch.fnmatch`,
    which folds the name through `os.path.normcase` - the identity on every POSIX platform,
    macOS included whatever its filesystem does, and a case fold ON WINDOWS - and would make
    membership a property of the machine the gate ran on."""
    parts = PurePosixPath(_posix(rel)).parts
    return (len(parts) == 3 and parts[0] == PROOF_ROOT
            and fnmatch.fnmatchcase(parts[2], pattern))


def spec_id_for_verdict(path):
    """`<proof root>/<spec id>/<name>` -> the spec id: THE MIDDLE of the three components the
    membership rule counts. IT LIVES WITH THE RULE because it reads the same shape, and a shape
    read in two modules is the divergence this one exists to prevent. It used to be UNVERIFIED
    (`a/b/c` -> `b`), so a path two directories deep named the WRONG component as its spec id;
    every path reaching the domain now satisfies corpus_member, which COUNTS the components. The
    guard stays: this is a string function anyone may call."""
    parts = str(path).split("/")
    return parts[1] if len(parts) > 2 else ""


def name_shaped(rel, pattern):
    """Whether a path under the proof root CARRIES A CORPUS NAME, at whatever depth.

    This is the complement `corpus_member` needs to be honest: a file named like a verdict
    that sits where the rule does not admit it is not silently ignored, it is REPORTED by
    `misfiled` and the gate is red on it. Narrowing a rule without naming what the narrowing
    dropped is how a review log stops recording without anybody noticing."""
    parts = PurePosixPath(_posix(rel)).parts
    return (len(parts) >= 2 and parts[0] == PROOF_ROOT
            and fnmatch.fnmatchcase(parts[-1], pattern))


def under_proof_root(rel):
    """Whether a path IS the declared proof root or lies beneath it, in the one spelling.

    Deliberately WEAKER than both membership predicates above: it asks only where a path sits,
    not what it is named or how deep it is, because it answers a question about the CORPUS
    LOCATION rather than about corpus membership. The proof root itself counts: a tracked symlink
    or gitlink AT the proof root is the one shape under which the working tree can hold a whole
    corpus that the index cannot name a single member of."""
    p = _posix(rel)
    return p == PROOF_ROOT or p.startswith(PROOF_ROOT + "/")


def _git_z(args, cwd):
    """One git read whose output is NUL delimited, returning (records, ok).

    `-z` IS LOAD BEARING AND NOT A STYLE CHOICE. git's default `core.quotePath` C quotes any
    path with a byte outside ASCII, so a tracked `proof/<dir with an accent>/verdict.json`
    comes back as a QUOTED, ESCAPED string that matches no real path and silently leaves the
    enumeration. Measured on the mechanism this replaces: such an artifact was validated
    and not entitled under its real spelling and entitled and not validated under its quoted
    one, which is a genuine review that can never be recorded. NUL delimited output is never
    quoted and is also the only form safe for a path containing a newline."""
    try:
        r = subprocess.run(["git"] + list(args), cwd=str(cwd), capture_output=True, text=True)
    except OSError:
        return [], False
    if r.returncode != 0:
        return [], False
    return [rec for rec in r.stdout.split("\0") if rec], True


def _git_line(args, cwd):
    """One git read whose answer is a single line, returning (line, ok). Separate from _git_z
    because `rev-parse` writes no NUL and an empty answer must be told from a failed call.

    EXACTLY ONE TRAILING NEWLINE COMES OFF, AND NO SURROUNDING WHITESPACE, which is a measured
    defect and not a tidiness preference. `rev-parse --show-prefix` answers a REPO-RELATIVE PATH,
    and a path component may begin or end with a space or a tab. `.strip()` turned a VELDO root at
    `" lead/"` into `"lead/"`, so the pathspec became `:(top,literal)lead/proof` - a directory
    that does not exist - and git ANSWERED SUCCESSFULLY WITH NOTHING: the entitlement domain
    silently became empty against a working tree of 167 artifacts, `validate.py all` exited 0
    printing nothing at all, and the reconciler reported `0 verdict artifact(s) tracked`. A
    SILENT WRONG ANSWER IS WORSE THAN A LOUD ONE, and this one had the same 166-to-0 signature as
    the anchoring defect the round before it. git terminates the answer with one newline, so one
    newline is what is removed, and what git returned is what this module reads."""
    try:
        r = subprocess.run(["git"] + list(args), cwd=str(cwd), capture_output=True, text=True)
    except OSError:
        return "", False
    if r.returncode != 0:
        return "", False
    out = r.stdout
    return (out[:-1] if out.endswith("\n") else out), True


def corpus_pathspec(root):
    """THE ONE ANCHORING, RESOLVED FROM THE VELDO ROOT: (pathspec, prefix, ok).

    `root` IS REQUIRED AND IS THE VELDO ROOT - the directory that owns the proof corpus and the
    event log - never a caller's cwd. Every git read below runs with this directory as its cwd
    and every path it answers with is made relative to it, so the disk half and the git half of
    any comparison cannot be given two different roots.

    THE PREFIX IS GIT'S OWN ANSWER, not string surgery: `rev-parse --show-prefix` says where
    `root` sits inside its repository, and the pathspec is that prefix plus the declared proof
    root under `:(top,literal)`. When the VELDO root IS the repository root the prefix is empty
    and the pathspec is the plain proof directory, which is the ordinary case and the one this
    repository runs. When it is not - VELDO vendored at `sub/` of a larger repository, which the
    scaffold supports - the pathspec still names the VENDORED proof root and never the outer
    one. That distinction is the whole of B2: read the other way, a forged verdict committed at
    the outer proof root was entitled to append to the vendored VELDO's own log.

    ok is False when git could not answer at all. A caller must not read that as an empty
    corpus: in a directory that is not a repository the domain is empty AND unavailable, and
    those are different facts."""
    prefix, ok = _git_line(["rev-parse", "--show-prefix"], root)
    return CORPUS_PATHSPEC_MAGIC + prefix + PROOF_ROOT, prefix, ok


def _nearest_existing(p):
    """The closest existing ancestor of a path, so a file whose directory has not been created
    yet still has a repository to be asked about."""
    p = Path(p).resolve()
    while not p.exists() and p != p.parent:
        p = p.parent
    return p


def veldo_root(path):
    """THE VELDO ROOT THAT OWNS A FILE: the root `corpus_pathspec` is resolved from, given
    something inside it. It lives here because the anchoring and the root the anchoring is taken
    from are one question, and answering them in two modules is how they would come apart.

    A VELDO root keeps its modules and its log in the engine directory, so the answer is the
    PARENT of the nearest ancestor-or-self of the file's directory that IS that engine directory,
    and the file's own directory when there is none. Ancestor-or-self and not the immediate
    parent: a caller may hand this a log in a scratch directory INSIDE the engine directory, and
    reading that scratch directory as a VELDO root of its own enumerates an EMPTY domain and
    withholds every genuine verdict, which is the inverse harm.

    IT IS NOT THE REPOSITORY ROOT AND MUST NOT BE ASSUMED TO BE ONE. VELDO vendored at `sub/` of a
    larger repository has its own corpus and its own log; anchoring at the repository root
    instead entitled a verdict committed at the OUTER proof root to append to the vendored log
    while `validate.py all` exited 0 on both sides of the append."""
    d = _nearest_existing(Path(path).parent)
    for cand in [d] + list(d.parents):
        if cand.name == VELDO_DIR:
            return cand.parent
    return d


def _relative(paths, prefix):
    """git's `--full-name` answers relative to the repository root; every path here is
    relative to the VELDO ROOT. The pathspec already restricts the answer to `<prefix>proof`,
    so the guard drops nothing in practice - it is here so that an answer which somehow did
    not carry the prefix is excluded rather than silently mis-measured by one component."""
    if not prefix:
        return list(paths)
    return [p[len(prefix):] for p in paths if p.startswith(prefix)]


def _tracked(root, pathspec, prefix):
    """(paths, ok) for every path git tracks under the VELDO root's proof directory."""
    paths, ok = _git_z(["ls-files", "-z", "--full-name", "--", pathspec], root)
    return _relative(paths, prefix), ok


def tracked_under_proof(root):
    """(paths, ok) for EVERY path git tracks under the proof root, unfiltered by name, as
    paths relative to the VELDO root.

    ok is False when git could not answer at all, which a caller must not read as an empty
    corpus: in a directory that is not a git repository the domain is empty AND the answer
    is unavailable, and those are different facts."""
    pathspec, prefix, _ok = corpus_pathspec(root)
    return _tracked(root, pathspec, prefix)


def tracked_direct(root):
    """(paths, ok): GIT'S OWN ANSWER TO `WHAT DO YOU TRACK HERE`, asked WITHOUT the corpus
    pathspec and WITHOUT this module's prefix arithmetic, as paths relative to the VELDO root.

    THIS IS A SECOND OPINION AND IT IS NOT A SECOND ENUMERATION. Nothing derives entitlement from
    it and no caller may: the domain remains the ONE pathspec-anchored reading above, so the
    spelling-and-anchoring class this module closes stays closed. Its only job is to answer the
    question the validated-not-entitled direction must ask SOMEBODY - IS THIS PATH TRACKED - from
    a source that is not the set under test.

    WHY IT HAD TO EXIST, MEASURED. `contradiction` was `(disk - tracked_members) - untracked` with
    `untracked = disk - tracked`, which reduces to `(disk - tracked_members) intersect tracked` and
    is IDENTICALLY EMPTY FOR EVERY POSSIBLE INPUT, because disk_corpus returns only members and
    tracked_members is tracked intersect members. The check inferred untracked-ness FROM THE VERY
    ENUMERATION IT WAS VALIDATING, so the direction the contract calls a contradiction could not
    fail for any repository, ever, and a vacuous assertion is worse than no assertion because it
    reads as coverage.

    IT IS INDEPENDENT OF THE PATHSPEC AND OF THE PREFIX ARITHMETIC, WHICH IS WHERE THE MEASURED
    DEFECTS LIVED, AND OF NOTHING ELSE. No pathspec, so a mangled or misanchored pathspec cannot
    silence it. No `--full-name`, so GIT spells the answer relative to its cwd - which is the VELDO
    root - and this module performs no prefix arithmetic on the result. IT IS NOT INDEPENDENT OF THE
    PROCESS ENVIRONMENT, and the independence claim needs that qualifier: with GIT_DIR and
    GIT_WORK_TREE pointed at another repository BOTH reads move together, measured over a victim root
    holding two artifacts against an attacker holding one, `contradiction` 0 and `overclaimed` 0
    while the domain became the attacker's. That shape is caught by the OLDER
    entitled_not_validated leg (1 entitled against 2 validated, so it reds) and the environment is
    declared as a limit at the foot of this module; it is not caught here.

    WHAT KEEPS THE OUTER REPOSITORY OUT IS GIT'S CWD RESTRICTION, AND THE SENTENCE THAT USED TO SAY
    OTHERWISE WAS MEASURED FALSE. git restricts a bare `ls-files` to the current directory and below,
    so a VELDO root vendored below the top of a larger repository is answered about ITSELF and the
    outer repository's own `proof/` IS NOT IN THE ANSWER AT ALL. Measured this round on git 2.43.0,
    VELDO vendored at `sub/` of an outer repository holding a forgery at
    `proof/WARP-9999/verdict.json`: the bare answer is 3 records, every one under `sub`, and ZERO of
    them begin with `../`. The sentence this replaces said the outer proof root `comes back as
    ../proof/...` and is refused for having four components; that describes a read this function does
    NOT perform, because the `../` spelling appears only once the cwd restriction is LIFTED by a
    pathspec (measured: `-- ':(top)'` from the same cwd answers `../proof/WARP-9999/verdict.json`).
    THE FOUR-COMPONENT REJECTION IS THEREFORE NOT LOAD BEARING HERE and nobody may treat it as the
    guard: the guard is that this read passes no pathspec.

    `--full-name` MUST NOT BE ADDED, and it is not the harmless spelling fix it looks like. It
    respells the answer from the top of the REPOSITORY, so a vendored VELDO root's own artifacts come
    back as `<prefix>proof/<id>/<name>` - four or more components - and the ONE membership rule
    admits NONE of them. Measured by adding the flag to a scratch copy of this module, 1
    substitution asserted present before any result was believed: the second opinion's member set
    went 2 -> 0, so both genuine artifacts turned up in `overclaimed` and the gate reds the whole
    REAL corpus, and `tracked_under_proof` went 2 -> 0, which also disarms the empty-domain leg. The
    three-component spelling the rule DOES admit becomes the OUTER root's: with the flag added and
    the cwd restriction also lifted, the outer forgery comes back as `proof/WARP-9999/verdict.json`
    and is the one record the rule admits (measured). The inverse harm and the forgery, from one flag.

    IT ANSWERS INDEX ENTRIES, NOT DISTINCT PATHS. `git ls-files` prints one record per index entry,
    so a CONFLICTED path appears once per stage: measured, one conflicted `proof/<id>/verdict.json`
    gives 3 records for 1 path. Every set built from this answer deduplicates, but a LENGTH taken
    from it counts ENTRIES, and any message quoting one has to say entries.

    Index entries hidden from the working tree by sparse-checkout ARE still reported (measured),
    which is what makes the two directions distinguishable: absent-from-disk is not the same fact as
    not-tracked.

    ok is False when git could not answer at all, and a caller must not read that as nothing being
    tracked."""
    return _git_z(["ls-files", "-z"], root)


def tracked_corpus(root, pattern=VERDICT_PATTERN):
    """THE DOMAIN: the corpus artifacts TRACKED IN GIT, derived at run time so it grows with
    the repository and no count is ever carried in code."""
    paths, _ok = tracked_under_proof(root)
    return sorted(p for p in paths if corpus_member(p, pattern))


def _index_entries(root, pathspec, prefix):
    """(path -> (mode, blob), ok) from the index, for every tracked path under the proof root.

    `git ls-files -s -z` writes `<mode> <sha> <stage>\\tpath` per NUL terminated record, so
    the path is taken after the TAB and never split on whitespace: a spec directory with a
    space in its name is a legal path and splitting the whole record would lose it."""
    recs, ok = _git_z(["ls-files", "-s", "-z", "--full-name", "--", pathspec], root)
    if not ok:
        return {}, False
    out = {}
    for rec in recs:
        meta, _, path = rec.partition("\t")
        fields = meta.split()
        if path and len(fields) >= 2:
            for rel in _relative([path], prefix):
                out[rel] = (fields[0], fields[1])
    return out, True


def tracked_index_entries(root):
    """(path -> (mode, blob), ok) from the index, relative to the VELDO root."""
    pathspec, prefix, _ok = corpus_pathspec(root)
    return _index_entries(root, pathspec, prefix)


def _staged(root, pathspec, prefix):
    """(paths, ok) for the tracked paths whose INDEX content differs from HEAD."""
    paths, ok = _git_z(["diff", "--cached", "--name-only", "-z", "HEAD", "--", pathspec], root)
    return _relative(paths, prefix), ok


def staged_under_proof(root):
    """(paths, ok) for the tracked paths whose INDEX content differs from HEAD. Keying one
    would write an event for a review that may never land, which an append-only log could
    not take back."""
    pathspec, prefix, _ok = corpus_pathspec(root)
    return _staged(root, pathspec, prefix)


def _is_object_name(s):
    """Whether a string is a git object name as index output spells one."""
    return len(s) == _OBJECT_NAME_LEN and all(c in _HEX for c in s)


def committed_blobs(root, pattern=VERDICT_PATTERN):
    """(path -> blob sha of its COMMITTED content, note, excluded) for the corpus artifacts this
    repository can key: a note naming why it could key NOTHING, and an excluded map naming, PER
    PATH, why that one path was left out.

    `git ls-files -s` reads the index, whose blob shas are byte-identical in a --depth 1 clone of
    the same commit (measured), because a blob sha is a property of content. THREE kinds of path
    are EXCLUDED, each with its own reason rather than one message covering several. A path
    carrying a STAGED change: its index blob is not what the repository has committed, and keying
    it would write an event for a review that may never land, which an append-only log could not
    take back. A path whose index mode is not a regular file. And A PATH THE WORKING TREE DOES NOT
    HOLD, which is the same argument as the staged one and was measured landing a forgery: with
    `git sparse-checkout set` naming every top level directory except the proof root, the index
    still held all 168 corpus artifacts while the working tree held NONE, so nothing validated any
    of them - `validate.py all` exited 0 having looked at no artifact at all - and a plain
    reconciler run appended a verdict.recorded carrying a real blob for a `{"schema": "nope",
    "verdict": "pass"}` committed at `proof/WARP-9999/verdict.json`. An append-only log cannot take
    that back, so A PATH THE VALIDATOR COULD NOT HAVE OPENED IS NOT KEYED: a member of only the
    index half is not appendable, it is DEFERRED with the reason named. The contract stage is
    separately red on it (entitled_not_validated), and this refusal does not depend on that stage
    having run.

    WHAT THAT EXCLUSION PROVES IS THAT THE PATH IS ON DISK, AND NOTHING MORE, which is why the
    sentence here used to overclaim: `THE BYTES MUST BE THERE TO BE KEYED` reads as though the keyed
    content had been seen by a validator, and it has not. The blob keyed is the INDEX blob; the bytes
    validated are the WORKING TREE's; when they differ, this function still keys the index blob and
    no check compares them. That is measured, PRE-EXISTING, declared in this module's known-open list
    and specified separately as WARP-0728. The three exclusions below are about the INDEX ENTRY and
    the PATH, never about content identity.

    IT LIVES HERE, NOT IN THE PROJECTION, because it is entirely a corpus and index question and
    this module is the only one that talks to git about the corpus. The set it offers is therefore
    the SAME enumeration entitlement is decided by, at the SAME anchoring, filtered by the SAME
    membership rule, and not a second reading of the index that could drift from the first. The
    path shape used to be UNCHECKED on this route: `proof/<a>/<b>/verdict.json` arrived with a
    real blob and was keyed."""
    head, ok = _git_line(["rev-parse", "--verify", "HEAD"], root)
    if not ok or not _is_object_name(head):
        return {}, "no commit in this repository yet", {}
    pathspec, prefix, _ok = corpus_pathspec(root)
    staged_paths, ok = _staged(root, pathspec, prefix)
    if not ok:
        return {}, "git could not compare the index with HEAD", {}
    staged = set(staged_paths)
    entries, ok = _index_entries(root, pathspec, prefix)
    if not ok:
        return {}, "git could not read the index", {}
    on_disk = set(disk_corpus(root, pattern))
    blobs, excluded = {}, {}
    for path, (mode, blob) in entries.items():
        if not corpus_member(path, pattern) or not _is_object_name(blob):
            continue
        if mode not in INDEX_FILE_MODES:
            excluded[path] = "index mode %s, not a regular file" % mode
        elif path in staged:
            excluded[path] = "staged, not committed"
        elif path not in on_disk:
            excluded[path] = "tracked but absent from the working tree, so nothing validated it"
        else:
            blobs[path] = blob
    return blobs, "", excluded


def corpus_in_dir(proof_dir, pattern=VERDICT_PATTERN):
    """The corpus artifacts under a NAMED proof directory, as absolute paths.

    THE ONE WALK AND THE ONE RULE, with the directory the caller named standing in for the
    declared proof root, so a caller holding a fixture tree gets the same membership decision
    as the repository does. Never a glob, so this side cannot acquire a wildcard whose reach
    differs from the git side's.

    EVERY DIRECTORY ENTRY IS CONSIDERED, NOT ONLY REGULAR FILES, and that is deliberate. The
    glob this replaced filtered by no file type either, so a directory or a FIFO at a corpus
    path was a member and its reader failed on it BY NAME. Filtering here would have made such
    a path silently absent from the validated set instead - the inverse harm again, and it would
    also have discarded what WARP-1210 measures, a FIFO at a corpus root that must be reported
    rather than hung on. The git side does not drop them either: a non-regular INDEX MODE is
    deferred with the mode named by committed_blobs, so both sides still hold the same set."""
    proof_dir = Path(proof_dir)
    out = []
    for dirpath, dirnames, filenames in os.walk(proof_dir):
        for name in list(dirnames) + list(filenames):
            p = Path(dirpath) / name
            try:
                rel = _posix(p.relative_to(proof_dir))
            except ValueError:
                continue
            if corpus_member(PROOF_ROOT + "/" + rel, pattern):
                out.append(p)
    return sorted(out)


def disk_corpus(root, pattern=VERDICT_PATTERN):
    """THE VALIDATED SET: the corpus artifacts PRESENT ON DISK under the proof root, as paths
    relative to root, which is the spelling the git side answers in so the two are comparable
    without either being rewritten at the comparison."""
    root = Path(root)
    return sorted(_posix(p.relative_to(root)) for p in corpus_in_dir(root / PROOF_ROOT, pattern))


def _misfiled(root, tracked, pattern):
    """misfiled, over an ALREADY ENUMERATED tracked list, so the caller that has one does not
    pay for a second git read and cannot accidentally pass a different root to the two halves."""
    seen = set(tracked)
    base = Path(root) / PROOF_ROOT
    for dirpath, dirnames, filenames in os.walk(base):
        for name in list(dirnames) + list(filenames):
            try:
                seen.add(_posix((Path(dirpath) / name).relative_to(Path(root))))
            except ValueError:
                continue
    return sorted(p for p in seen if name_shaped(p, pattern) and not corpus_member(p, pattern))


def misfiled(root, pattern=VERDICT_PATTERN):
    """Every path under the proof root that CARRIES a corpus name but is not a corpus
    member, from either source, sorted and deduplicated.

    ONE ROOT SERVES BOTH SOURCES and there is no second parameter to disagree with it. There
    used to be: the projection called this with the disk half at its own root and the git half
    at the process cwd IN ONE CALL, and reconciling this repository from a foreign repository's
    directory printed a misfiled warning naming a path that exists only over there.

    This is what the shipped git pathspec used to admit into the entitlement domain and the
    validator never saw. It is not ignored here: it is named, and the contract stage is red
    on it, because an artifact at such a path can never be recorded as a review and a
    verdict nobody can record is worse than a verdict that does not exist."""
    tracked, _ok = tracked_under_proof(root)
    return _misfiled(root, tracked, pattern)


def divergence(root, pattern=VERDICT_PATTERN):
    """THE TWO SETS AND THEIR DIFFERENCE IN BOTH DIRECTIONS, over the real corpus.

    ONE ROOT, so the git side and the disk side are the same directory by construction and the
    question asked of each is the question entitlement is decided by, at the one anchoring.

    THE TRACKED-OR-NOT QUESTION IS PUT TO GIT AND NEVER TO THE ENUMERATION UNDER TEST, which is
    the whole of what `tracked_direct` is for and the reason the contradiction leg below can fail
    at all. Deriving it from the domain made it arithmetically empty for every possible input. The
    two readings are independent OF THE PATHSPEC AND THE PREFIX ARITHMETIC, not of the process
    environment: a redirected GIT_DIR or GIT_WORK_TREE moves both together, measured, and that limit
    is declared at the foot of this module rather than covered here.

    Returns a dict carrying, by name:
      git_available          whether BOTH git reads answered. When either did not, the domain is
                             EMPTY BY THE SAME ABSENCE that makes this unanswerable, so
                             there is nothing a projection could append and containment
                             holds vacuously rather than being waived. That soundness is
                             the whole payoff of one owner: the two sides degrade together.
                             The equality legs below are then INERT, so a caller that reports
                             a green must SAY SO rather than let a skipped check read as a
                             passed one.
      entitled_not_validated the domain members no validator will ever see. THE FORGERY
                             DIRECTION, and it must be empty. Reached with sparse-checkout:
                             the index holds the whole corpus and the working tree holds none
                             of it.
      validated_not_entitled the artifacts validated but outside the domain, so no review
                             event can ever be derived for them. THE INVERSE HARM DIRECTION,
                             partitioned below by WHAT GIT SAYS about each path rather than by
                             what the domain says.
      untracked              the validated artifacts GIT ITSELF does not report as tracked.
                             Expected and not red: an author validating before committing is
                             the normal flow.
      contradiction          the corpus members GIT REPORTS AS TRACKED that the enumerated
                             domain does not hold. Tracked plus the rule IS the domain, so any
                             member here is a live disagreement between two readings of one
                             index and the gate is red on it, per path.
      overclaimed            the reverse: domain members git's own answer does not report as
                             tracked under this root at all. The domain reaching OUTSIDE the
                             VELDO root is exactly how a verdict committed at an outer proof
                             root became entitled to append to a vendored log.
      tracked_under_proof    every INDEX ENTRY git reports AT OR BELOW the proof root, at any depth
                             and under any name. It is what tells an empty domain against a
                             non-empty working tree apart from an empty domain in a repository
                             that has simply committed nothing yet. ENTRIES, NOT DISTINCT PATHS: a
                             conflicted path carries one entry per stage and appears three times
                             (measured), so a caller reporting a LENGTH from this list must say
                             entries rather than paths.
      misfiled               name shaped, not a member, from either source.
    """
    tracked, ok = tracked_under_proof(root)
    direct, direct_ok = tracked_direct(root)
    tracked_set = {p for p in tracked if corpus_member(p, pattern)}
    disk_set = set(disk_corpus(root, pattern))
    direct_set = {p for p in direct if corpus_member(p, pattern)}
    return {
        "git_available": ok and direct_ok,
        "entitled": sorted(tracked_set),
        "validated": sorted(disk_set),
        "entitled_not_validated": sorted(tracked_set - disk_set),
        "validated_not_entitled": sorted(disk_set - tracked_set),
        "untracked": sorted(disk_set - set(direct)),
        "contradiction": sorted(direct_set - tracked_set),
        "overclaimed": sorted(tracked_set - direct_set),
        "tracked_under_proof": sorted(p for p in direct if under_proof_root(p)),
        "misfiled": _misfiled(root, tracked, pattern),
    }


def handle_is_the_named_file(fh, path):
    """(same, why): is the OPEN HANDLE the very file `path` names, without following a link at
    the final component?

    WHY THIS EXISTS. Entitlement is computed from the log's path, and `veldo_root` reads
    `Path(log).parent` - the PARENT - so a link at the FINAL component does not move it. The
    append, `open(log, "a+")`, DOES follow that final component. Measured at b0fa073 in a scratch
    directory: with a symlink at a victim's `.veldo/events.jsonl` pointing at another repository's
    log, `veldo_root` answered the victim root while the same open wrote the other file, st_ino
    28867751 opened against st_ino 28867752 for the path itself. The domain was enumerated for one
    repository and the bytes went to another. A path is a description of a file, not the file.

    THE COMPARISON IS BY IDENTITY AND THE AUTHORITY IS THE DESCRIPTOR: `os.fstat` on the handle
    that will be written against `os.stat(..., follow_symlinks=False)` on the name, by
    `(st_dev, st_ino)`. Taking it from the descriptor rather than re-reading the name is what also
    closes the swap between the check and the write; a second look at a string cannot, because the
    string can name a different file by the time the bytes move.

    DECLARED, NOT DEFENDED AGAINST: a platform whose `st_ino` does not distinguish files cannot
    answer this, and it says so (`same=False` with the reason named) rather than passing vacuously,
    because a guard that cannot tell must not report that it checked."""
    try:
        a = os.fstat(fh.fileno())
    except OSError as ex:
        return False, "could not stat the open log handle: %s" % (ex,)
    try:
        b = os.stat(path, follow_symlinks=False)
    except OSError as ex:
        return False, "could not stat %s without following links: %s" % (path, ex)
    if not a.st_ino or not b.st_ino:
        return False, ("this platform reports no usable st_ino, so the handle cannot be shown to "
                       "be the file %s names; refusing rather than assuming" % (path,))
    if (a.st_dev, a.st_ino) != (b.st_dev, b.st_ino):
        return False, ("the log opened for append is NOT the file %s names - opened "
                       "dev=%s ino=%s, the name is dev=%s ino=%s - so the entitlement was "
                       "enumerated for one repository and the bytes would land in another"
                       % (path, a.st_dev, a.st_ino, b.st_dev, b.st_ino))
    return True, ""
