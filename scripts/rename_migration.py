#!/usr/bin/env python3
"""The WARP -> Veldo rename, as a migration with a proven reverse (WARP-1702, W2 of PLAN-0017).

    python3 scripts/rename_migration.py --plan          # what would change, nothing written
    python3 scripts/rename_migration.py --apply DEST    # migrate a COPY at DEST
    python3 scripts/rename_migration.py --reverse DEST  # migrate it back
    python3 scripts/rename_migration.py --verify DEST   # DEST reversed == this repository

**WHY THIS IS NOT A GLOBAL FIND AND REPLACE, MEASURED.** This repository holds 11,683 references of
the form `WARP-1234`, and every one of them is a SPECIFICATION ID that must survive: an id is an
immutable reference that proofs, plans and cross-links all cite. Against those sit 7,988 `.warp/`
path references and 2,900 `warp.<name>/v<n>` schema ids that must all change. They share files and
frequently share LINES. A `sed s/warp/veldo/` destroys the corpus.

So every rule here is ANCHORED to a surface: a path prefix, a schema-id shape, a command name. The
bare-word rule runs LAST and only after the anchored ones have consumed everything they own, and it
refuses to touch a `WARP-` followed by digits.

**ORDER IS LOAD BEARING.** Longest and most specific first. Rewriting the bare word before the
schema ids would turn `warp.spec/v1` into `veldo.spec/v1` by accident and leave nothing for the
schema rule to verify, which means the verification would pass on a coincidence.

**THE REVERSE IS THE PROOF.** Every rule is a pair. `--verify` applies the migration to a copy,
applies the reverse, and asserts the result is byte-identical to the original for every file. A
migration whose reverse does not reproduce the input has lost or invented something, and no amount
of reading the diff establishes that as reliably as the round trip does.

**IT NEVER TOUCHES THE LIVE REPOSITORY.** `--apply` requires an explicit destination and refuses to
run in place. The live cutover is a separate, deliberate act.

**STATUS 2026-08-09: THE REVERSE IS PROVEN AND FORWARD COVERAGE IS COMPLETE.** Outside `proof/`
the 9 remaining occurrences are all deliberate test fixtures. What the cutover waits on is the
gate being green on the OTHER side, not the substitutions landing: selftest assertions carry old
paths and module names as strings, `specs/index.md` and the generated proof documents need
regenerating, and the path renames must reach the template tree in the same pass. Dmitry chose
8A on 2026-08-09: both commit-trailer spellings are accepted for a transition window, so the
push check does not refuse every pre-rename commit.

`--verify` now passes: 1,235 files compared, 16,501 edits recorded, **0 mismatched**. The reverse is
exact. What fixed it is below; what remains is forward COVERAGE, a different problem.

**WHY A SYMMETRIC REVERSE WAS IMPOSSIBLE, and what replaced it.** This repository ALREADY CONTAINS
the target name - 124 mentions of "Veldo" across 38 files, including PLAN-0017's own filename and
the VEL ticket references. So the forward transform is NOT INJECTIVE: afterwards, a "Veldo" in the
tree may be one this migration created or one that was always there, and a rule-based reverse
cannot tell them apart. It rewrote the pre-existing ones to "Warp" and corrupted them, 39 files'
worth. No rule tuning fixes that, because the information the reverse needs is not in the migrated
text.

The reverse is now MANIFEST-DRIVEN: `rewrite_forward` records every edit as (start, end, original)
in the OUTPUT's coordinates, per rule pass, and `rewrite_reverse` replays that record backwards -
passes in reverse order, edits within a pass in reverse order, so offsets stay valid. It refuses to
run without a manifest rather than falling back to guessing.

**TWO FURTHER BUGS THE ROUND TRIP CAUGHT, both silent corruptions rather than errors:**

  ORDER IS OPPOSITE IN THE TWO DIRECTIONS. Forward rewrites contents then moves paths; the reverse
  must move paths BACK FIRST, because the manifest is keyed by the ORIGINAL relative path. After the
  forward move `.warp/x.py` is on disk as `.veldo/x.py`, the lookup misses, and every file under the
  renamed directory is silently left un-reversed. That took the round trip from 39 mismatches to 118
  before the order was fixed.

  THE COMPARISON BASELINE WAS WRONG. `verify` compared the round-tripped clone against ROOT's live
  files, but the clone comes from HEAD, so uncommitted edits and a gate-written ledger showed up as
  two phantom mismatches. It now snapshots the clone and measures the round trip against its own
  starting point.

**A THIRD FORM OF THE SPEC-ID BUG: THE PREFIX PATTERN.** `glob("WARP-*.md")` has no digits to
protect it, so the bare-word rule renamed it to `VELDO-*.md` while the spec FILES correctly kept
`WARP-`. Every spec glob then matched nothing, which silently emptied the TOE corpus and aborted the
suite 918 lines in. Any `WARP-` followed by a wildcard, a format placeholder or a quote is an ID
PATTERN and is now masked exactly like the ids it matches. Fixing it took the suite from an abort at
line 918 to running nearly to the end.

**TWO MORE ANCHOR BUGS FIXED, both found by actually running the migrated tree.** The spec-id mask
used `\b` AFTER the digits too, so `warp_0623_codified_live` was not protected and the rename
invented `veldo_0623`, a specification id that does not exist. And `PATH_RENAMES` was a hand-listed
five entries, which missed all ten suite files: `suites/manifest.json` was rewritten to name
`01_veldo_0101_...` while `01_warp_0101_...` still sat on disk, and the runner refused to start.
Path renames are now DERIVED from the same rules applied to the path, 307 of them, and the reverse
replays the recorded pairs rather than re-deriving them from an already-renamed tree.

**THAT CLAIM OF COMPLETE COVERAGE WAS WRONG, AND HOW IT WAS WRONG IS THE USEFUL PART.** It read
"coverage is now complete: 9 occurrences remain and every one is a deliberate test fixture", and it
named three. Two of the three were defects wearing a decision's clothes. The `Warp-Task:` trailer was
an ANCHOR BUG: in `"Warp-Agent: a\nWarp-Task: b"` the `\n` puts a literal `n` before the name, so no
`\b` rule fired, and one string literal came out of the migration holding both names at once. The
`warp_%s_mut` aliases were missed because `%` is not a word character. Neither was deliberate;
counting them as fixtures is how a coverage gap gets ratified as an intention. The rule
set closed the gap in stages, and each stage was one anchor problem: `\b` does not fire between `_`
and a letter, so `_warp_bin`, `WARP_RUNS_ROOT`, `FILE_STATUS_TO_WARP`, `WARPRunLens` and
`warp1210teeth` each survived a rule that looked like it should have caught them.

**THIS FILE EXCLUDES ITSELF.** Its rule table holds the old name as literal regex source; rewriting
that would destroy the definitions driving the rename.

**WHAT REMAINS BEFORE THE CUTOVER: the migrated tree does not gate green yet.** Running the full
gate on a migrated copy gives three failure classes, all expected and all mechanical:

  1. `unit` - 25 failures and still one abort (`KeyError: 'scale_pool'`). The suite now runs most
     of the way. What is left splits into classes, and the biggest one is SELF-REFERENTIAL and
     cannot be fixed by a better rule:

       WARP-1701's own assertions test the rename guard using literal old-name and new-name
       strings. Migrating them inverts what they mean: a fixture that seeds the old name to prove
       it is caught becomes a fixture seeding the NEW name, and its control asserting the renamed
       surface is clean then fails by construction. The naming-contract suite and the migrator's
       fixtures have to be EXCLUDED from migration and rewritten by hand, the same way this file
       excludes itself.

       WARP-1308's `Warp-Agent:` / `Warp-Task:` trailer constants are protocol strings, and whether
       they rename was a DECISION rather than a substitution. **RESOLVED by Dmitry 2026-08-03:
       "Veldo going forward."** So they are NOT excluded - the ordinary bare-word rule renames them
       to `Veldo-Agent:` / `Veldo-Task:` (all three: agent, task, model).

       BUT THE TRANSITION IS NOT FREE, and a first draft of this note claimed it was. MEASURED, not
       assumed: with the renamed constants, a pre-rename commit carrying `Warp-Agent:` reports
       `commit_names_no_actor` and `commit_names_no_task`. So `check_range` over a push range that
       SPANS the rename will refuse every commit before it. Whoever lands the cutover has to pick
       one: teach `commit_attribution` to accept both spellings for a transition window, or start
       attribution enforcement at the rename commit. It is a small decision, but it is a decision,
       and finding it after enabling enforcement would be an unpleasant surprise.

       WARP-1311 asserts eleven shipped work items by reading spec front matter; it needs re-running
       rather than reasoning about.

       `KeyError: 'scale_pool'` is undiagnosed.
  2. `generated` - `specs/index.md` and the generated proof documents are stale and need
     regenerating after the rename, which is a command, not a decision.
  3. `template sync` - path renames must reach the template tree, which the derived
     `path_renames()` now does; re-measure after 1 is fixed.

None of these is a design problem. They are the ordinary tail of a rename this size, and they are
listed here so whoever runs the cutover knows the work is finished only when the gate is green on
the OTHER side, not when the substitutions land.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Binary and generated content that must be copied, never rewritten.
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".ico", ".woff", ".woff2", ".zip",
                 ".gz", ".bin", ".sqlite3", ".db", ".pyc", ".jsonl"}

# THE SPEC-ID GUARD. Anything matching this is an immutable identifier and is protected from every
# rule below by being masked out before substitution and restored afterwards.
# A specification id appears in THREE forms and all three are immutable references: the
# canonical `WARP-0623`, the lowercase underscore form suite filenames use
# (`13_warp_0623_codified_live.py`), and the same form inside identifiers. Missing the
# lowercase form renamed 136 files' worth of what are actually id references.
# NOTE THE ANCHOR. `\bwarp_0623\b` does NOT match inside `13_warp_0623_codified_live`,
# because `_` is a word character so there is no boundary before `warp`. Requiring one
# silently missed every suite filename, which is where most of these ids live.
# `\b` fails AFTER the digits too when an underscore follows: `warp_0623_codified_live` is a
# reference to WARP-0623 and renaming it invents a spec id that does not exist. Use a
# not-a-digit lookahead instead of a word boundary at both ends.
# THE PREFIX FORM TOO. `glob("WARP-*.md")` has no digits to protect it, so the bare-word rule
# renamed it to `VELDO-*.md` while the spec FILES correctly kept `WARP-`. Every spec glob
# then matched nothing, which is what emptied the TOE corpus and aborted the suite. Any
# `WARP-` followed by a wildcard, a format placeholder or a quote is an ID PATTERN and is
# just as immutable as the ids it matches.
# A PARTIAL numeric prefix is still an id pattern. `WARP-13\d\d` and `WARP-13%02d` name the
# eleven WARP-13xx specs, but only two digits are spelled out, so the `\d{3,4}` alternative does not
# fire and the bare-word rule renamed them to `VELDO-13...` while the spec FILES correctly kept
# `WARP-`. The glob then matched nothing and `next()` raised StopIteration.
# THE QUOTE IS NOT A PATTERN CHARACTER, which is the distinction I got wrong first. Allowing digits
# before ANY of the metacharacters also froze `"WARP-9"`, a one-digit synthetic id in a fixture,
# while the same id in `"WARP-9-x.md"` renamed, so the seed and the assertion disagreed and two
# passing selftests broke. A quote after the digits means a COMPLETE id, which either matches the
# canonical rule or is a fixture that may rename; only `* ? % { \` mean a pattern. So the
# no-digit form keeps the quotes and the digits form takes the pattern characters alone.
SPEC_ID = re.compile(r"WARP-\d{3,4}(?!\d)|(?i:warp)_\d{3,4}(?!\d)"
                     r"|WARP-(?=[*?%{\"'])|WARP-\d{1,4}(?=[*?%{\\])"
                     r"|(?i:warp)_(?=%[0-9]*d)")
_MASK = "\x00SPECID%d\x00"

# Masked for a DIFFERENT REASON: to create a word boundary, not to protect a reference. In the file
# text, `"Warp-Agent: a\nWarp-Task: b"` carries a literal `n` immediately before the second name, so
# `\bWarp\b` sees `nWarp`, finds no boundary, and EVERY anchored rule silently skips it. That is how
# one string literal came out of the migration holding both names at once. Masking the escape puts
# the sentinel's non-word terminator there instead, so the boundary fires and the rule applies. This
# is the third anchor bug of the same family, after the underscore and the id-pattern cases, and the
# lesson is the same: `\b` describes the CHARACTERS, and source text is not the string it denotes.
ESCAPE = re.compile(r"\\[nrt]")
_EMASK = "\x00ESC%d\x00"

# The ordered rule pairs. (forward_pattern, forward_repl, reverse_pattern, reverse_repl).
# MOST SPECIFIC FIRST. Each is anchored to a surface class from the WARP-1701 naming contract.
RULES = [
    # state directory
    (r"\.warp/", ".veldo/", r"\.veldo/", ".warp/"),
    (r'"\.warp"', '".veldo"', r'"\.veldo"', '".warp"'),
    # schema identifiers: warp.<name>/v<n>
    (r"\bwarp\.([a-z_]+)/v(\d)", r"veldo.\1/v\2", r"\bveldo\.([a-z_]+)/v(\d)", r"warp.\1/v\2"),
    # the command, its guard and its gate workflow
    (r"\bbin/warp\b", "bin/veldo", r"\bbin/veldo\b", "bin/warp"),
    (r"\bwarp-guard\b", "veldo-guard", r"\bveldo-guard\b", "warp-guard"),
    (r"\bwarp-gate\b", "veldo-gate", r"\bveldo-gate\b", "warp-gate"),
    (r"\bwarp-visual\b", "veldo-visual", r"\bveldo-visual\b", "warp-visual"),
    (r"\bwarp-web-runner\b", "veldo-web-runner", r"\bveldo-web-runner\b", "warp-web-runner"),
    # python identifiers and module aliases: warp_thing -> veldo_thing
    (r"\bwarp_([a-z0-9_]+)", r"veldo_\1", r"\bveldo_([a-z0-9_]+)", r"warp_\1"),
    (r"\bwarp_android_runner\b", "veldo_android_runner",
     r"\bveldo_android_runner\b", "warp_android_runner"),
    # A FORMAT PLACEHOLDER IS NOT A WORD CHARACTER, so `warp_%s_mut` fell through every rule: the
    # identifier rule needs `[a-z0-9_]` after the underscore and `%` is not that, and `\bwarp\b`
    # finds no boundary before the trailing `_`. These are module aliases for exec'd fixtures, and
    # one suite ASSERTS the alias it built, so producer and assertion rename together. The spec-id
    # mask above takes `warp_%04d` first, because that form would be an id template, not an alias.
    (r"\bwarp_(?=%)", "veldo_", r"\bveldo_(?=%)", "warp_"),
    # the skill namespace
    (r"/warp:", "/veldo:", r"/veldo:", "/warp:"),
    (r"\bwarp\.md\b", "veldo.md", r"\bveldo\.md\b", "warp.md"),
    # UNDERSCORE-ADJACENT IDENTIFIERS. `\b` does not fire between `_` and `warp`, because `_` is a
    # word character, so `_warp_bin` and `WARP_RUNS_ROOT` survived every rule above. The spec-id
    # mask has already removed `warp_0623`-shaped ids by this point, so what is left here is the
    # product name inside an identifier and it renames.
    (r"WARP_([A-Z0-9_]+)", r"VELDO_\1", r"VELDO_([A-Z0-9_]+)", r"WARP_\1"),
    (r"_warp_", "_veldo_", r"_veldo_", "_warp_"),
    (r"_warp\b", "_veldo", r"_veldo\b", "_warp"),
    # TRAILING and CONCATENATED forms the boundary rules also miss: `FILE_STATUS_TO_WARP`,
    # `WARPRunLens/1`, `warp1210teeth`. Same cause, other end of the identifier.
    (r"_WARP\b", "_VELDO", r"_VELDO\b", "_WARP"),
    (r"WARP(?=[A-Z][a-z])", "Veldo", r"Veldo(?=[A-Z][a-z])", "WARP"),
    (r"warp(?=\d)", "veldo", r"veldo(?=\d)", "warp"),
    (r"warp(?=status)", "veldo", r"veldo(?=status)", "warp"),
    # the bare word, LAST, after every anchored rule has taken what it owns. The spec-id mask makes
    # this safe; without it this single rule would corrupt 11,683 identifiers.
    (r"\bWARP\b", "VELDO", r"\bVELDO\b", "WARP"),
    (r"\bWarp\b", "Veldo", r"\bVeldo\b", "Warp"),
    (r"\bwarp\b", "veldo", r"\bveldo\b", "warp"),
]

# Paths are renamed by THE SAME RULES applied to the path string, never a hand-maintained list.
# The hand list missed all ten suite files, so `suites/manifest.json` was rewritten to name
# `01_veldo_0101_...` while `01_warp_0101_...` still sat on disk, and the runner refused to start.
# Deriving it means a path and its references can never disagree.
def path_renames(dest):
    """(old_rel, new_rel) for every tracked path whose name changes under the rules, longest first
    so a nested path moves before its parent."""
    out = []
    for rel in tracked_files(dest):
        new = rewrite_path(rel)
        if new != rel:
            out.append((rel, new))
    # Directories are not tracked as entries, so add the ones that must move wholesale.
    for d in (".warp",):
        if (Path(dest) / d).exists():
            out.append((d, rewrite_path(d)))
    return sorted(out, key=lambda pair: -len(pair[0]))


def rewrite_path(rel):
    """Apply the rules to a PATH. Spec ids are masked here too: a suite file named for WARP-0623
    keeps that id, because renaming it would point at a specification that does not exist."""
    masked, found = _mask_spec_ids(rel)
    for fwd_pat, fwd_rep, _rp, _rr in RULES:
        masked = re.sub(fwd_pat, fwd_rep, masked)
    return _unmask(masked, found)


def _mask_spec_ids(text):
    """Mask spec ids so no rule can reach them, and escape sequences so the rules can.

    Two masks, two purposes, kept separate so the spec-id count stays an honest count of protected
    references. Returns (masked, (ids, escapes)) and _unmask restores both."""
    ids, escapes = [], []

    def take_id(m):
        ids.append(m.group(0))
        return _MASK % (len(ids) - 1)

    def take_esc(m):
        escapes.append(m.group(0))
        return _EMASK % (len(escapes) - 1)

    # ESCAPES FIRST, and the order is load-bearing. `id: WARP-9\nstatus` is an id followed by an
    # escape, while `WARP-13\d\d` is an id PATTERN; both put a backslash after the digits, so
    # masking ids first cannot tell them apart and it masked `WARP-9` as a pattern while the
    # matching filename `WARP-9-x.md` renamed, leaving the id and its file disagreeing. Masking the
    # escape first replaces it with a non-metacharacter sentinel, so only a REAL `\d` still reads
    # as a pattern. Found by two selftests that were passing before this function changed.
    return SPEC_ID.sub(take_id, ESCAPE.sub(take_esc, text)), (ids, escapes)


def _unmask(text, found):
    ids, escapes = found
    for i, original in enumerate(escapes):
        text = text.replace(_EMASK % i, original)
    for i, original in enumerate(ids):
        text = text.replace(_MASK % i, original)
    return text


def _sub_recording(pattern, repl, text):
    """re.sub, but it also returns what it destroyed and WHERE, in the OUTPUT's coordinates.

    Each edit is (start, end, original) with start/end indexing the NEW text, so undoing is a
    straight splice. This is the whole mechanism that makes the reverse exact."""
    out, edits, pos, new_pos = [], [], 0, 0
    for m in re.finditer(pattern, text):
        out.append(text[pos:m.start()])
        new_pos += m.start() - pos
        replacement = m.expand(repl)
        out.append(replacement)
        edits.append((new_pos, new_pos + len(replacement), m.group(0)))
        new_pos += len(replacement)
        pos = m.end()
    out.append(text[pos:])
    return "".join(out), edits


def rewrite_forward(text):
    """Apply every rule in order and RECORD every edit, per pass.

    Returns (new_text, passes) where passes[i] is the edit list for RULES[i]. The reverse replays
    it; it does not re-derive it. That is the fix for the non-injectivity: a "Veldo" this pass
    created is in the record, and a "Veldo" that was always in the file is not, so the reverse can
    finally tell them apart."""
    masked, found = _mask_spec_ids(text)
    passes = []
    for fwd_pat, fwd_rep, _rp, _rr in RULES:
        masked, edits = _sub_recording(fwd_pat, fwd_rep, masked)
        passes.append(edits)
    return _unmask(masked, found), passes


def rewrite_reverse(text, passes):
    """Undo a recorded forward pass exactly: passes backwards, and edits within a pass backwards so
    the offsets of the not-yet-undone edits stay valid."""
    masked, found = _mask_spec_ids(text)
    for edits in reversed(passes):
        for start, end, original in reversed(edits):
            masked = masked[:start] + original + masked[end:]
    return _unmask(masked, found)


def rewrite(text, reverse=False):
    """The symmetric form, kept ONLY for the plan display. It is NOT sound for a real reverse on
    this repository (see the module docstring): the tree already contains the target name."""
    masked, found = _mask_spec_ids(text)
    for fwd_pat, fwd_rep, rev_pat, rev_rep in RULES:
        pat, rep = (rev_pat, rev_rep) if reverse else (fwd_pat, fwd_rep)
        masked = re.sub(pat, rep, masked)
    return _unmask(masked, found)


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracked_files(root):
    out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"],
                         capture_output=True, text=True).stdout
    return [p for p in out.split("\0") if p]


# A MIGRATION TOOL DOES NOT MIGRATE ITSELF. This file's rule table contains the old name as literal
# regex source; rewriting it would destroy the very definitions that drive the rename. Excluded by
# path, deliberately, and it is the only self-referential exclusion.
SELF = "scripts/rename_migration.py"


# THE PROOF CORPUS IS EVIDENCE AND THE CONTRACT SAYS SO. `.warp/naming.py` NOT_RENAMED records the
# reason in its own words: "evidence records what was true when it was recorded. A renamed schema
# identifier must not invalidate evidence already on the record." Two paragraphs of this file's own
# docstring ALREADY claimed the migration works "outside proof/". It did not. There was no exclusion
# in the code, and 380 evidence files were rewritten: schema ids, and the recorded prose of what
# reviewers actually wrote. That inverted the corpus, 114 of 120 proof digests matching before and 6
# after, because each manifest was edited out from under the verdict bound to it.
#
# The tempting fix is to recompute the 114 digests. THAT WOULD BE THE WRONG FIX and it is worth
# saying why: re-stamping a digest re-binds a human reviewer's verdict to text that reviewer never
# read. The evidence would look valid and would no longer be evidence. Excluding the corpus keeps
# every digest valid without touching a single verdict.
#
# A comment claiming an exclusion is not an exclusion. This is the code.
NOT_RENAMED_PATHS = ("proof/",)


def _is_text(rel):
    if rel == SELF or rel.startswith(NOT_RENAMED_PATHS):
        return False
    return Path(rel).suffix.lower() not in SKIP_SUFFIXES


# A REVIEWED ARTIFACT BINDS A HUMAN JUDGEMENT TO EXACT CONTENT. Matching the FIELD, never prose:
# capabilities.yaml discusses `reviewed_digest` at length inside a note and carries none.
REVIEWED_DIGEST_FIELD = re.compile(r"^(\s*reviewed_digest:\s*)(\S+)[ \t]*$", re.M)

# The ONLY fields a rename may legitimately move inside a reviewed action. Everything absent from
# this set is the safety envelope a human actually judged: the system acted upon, the typed
# parameters and their constraints, the risk class, the reversibility analysis, the rollback plan and
# the canary. If the rename reaches any of those, the recorded review has stopped describing the
# artifact and the correct answer is a new human review, not a new digest.
NAME_BEARING_FIELDS = frozenset(["schema"])


# A reviewed artifact is a RECORD, not code. Without this, the scan matched the suite that asserts
# over these examples, because it holds a digest literal, and the parser was then handed Python.
RECORD_SUFFIXES = (".yaml", ".yml", ".json")


def reviewed_artifacts(dest):
    """Tracked RECORDS carrying a real reviewed_digest field, in path order."""
    out = []
    for rel in tracked_files(dest):
        p = Path(dest) / rel
        if not p.is_file() or not _is_text(rel) or not rel.endswith(RECORD_SUFFIXES):
            continue
        try:
            text = p.read_text("utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if REVIEWED_DIGEST_FIELD.search(text):
            out.append(rel)
    return out


def action_payload_reader(dest):
    """Build the payload reader from THE TREE'S OWN action module, never a second implementation.

    `action_digest` is the artifact's canonical digest and there must be exactly one of it; a copy
    here would drift from the store that enforces it and the re-stamp would certify a digest the
    store rejects. action.py takes its parser injected, so validate.py is loaded alongside it. Paths
    are resolved AFTER the move, so this reads the migrated tree."""
    import importlib.util

    def load(rel):
        path = Path(dest) / rewrite_path(rel)
        spec = importlib.util.spec_from_file_location("rn_" + Path(rel).stem, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    V, ACT = load(".warp/validate.py"), load(".warp/action.py")

    def payload_of(text):
        data = V.parse_yamlish(text)
        return {"digest": ACT.action_digest(data),
                "fields": {k: v for k, v in data.items() if k != "review"}}

    return payload_of


def restamp_reviews(dest, pre_texts, digest_of):
    """Re-stamp the reviews the rename invalidated, and REFUSE rather than launder one.

    The rename edits an action's schema id, which is inside the digest the recorded review binds
    to, so the store correctly reports every reviewed action as STALE afterwards. There is
    deliberately no tool in the repository to re-stamp one, because the design intends a HUMAN to
    re-review. This carries a human's standing decision across a pure rename, and it is allowed to
    do that ONLY under two proofs, each of which REFUSES instead of proceeding:

      1. THE REVIEW WAS VALID BEFORE. Recorded digest equals the digest of the PRE-rename content.
         Re-stamping an already-stale review would manufacture a review nobody performed, which is
         the exact failure the drift guard exists to prevent.
      2. ONLY A NAME-BEARING FIELD MOVED. Every field whose value differs between the pre- and
         post-rename content must be in NAME_BEARING_FIELDS, so the SAFETY ENVELOPE the reviewer
         actually judged (the system, the parameters and their constraints, the risk class, the
         reversibility, the rollback plan, the canary) is proven byte-identical. Comparing rewritten
         text against the migrated file would be VACUOUS, because the migrated file IS the rewritten
         text; asking which FIELDS moved is the question with an answer that can come back no.

    Returns [(rel, old_digest, new_digest)]. Raises SystemExit naming the file on either refusal."""
    out = []
    for rel in sorted(pre_texts):
        p = Path(dest) / rewrite_path(rel)
        if not p.exists():
            raise SystemExit("restamp: %s vanished after the rename; refusing to guess" % rel)
        post = p.read_text("utf-8")
        pre = pre_texts[rel]
        recorded = REVIEWED_DIGEST_FIELD.search(pre)
        if not recorded:
            continue
        was = recorded.group(2)
        pre_payload, post_payload = digest_of(pre), digest_of(post)
        if pre_payload["digest"] != was:
            raise SystemExit(
                "restamp: %s was ALREADY STALE before the migration (recorded %s, content %s). "
                "Re-stamping it would launder a review nobody performed. Re-review it by hand."
                % (rel, was, pre_payload["digest"]))
        pf, qf = pre_payload["fields"], post_payload["fields"]
        if set(pf) != set(qf):
            raise SystemExit("restamp: %s gained or lost a field in its reviewed substance (%s); the "
                             "recorded review does not cover it. Re-review it by hand."
                             % (rel, sorted(set(pf) ^ set(qf))))
        moved = sorted(k for k in pf if pf[k] != qf[k])
        if [k for k in moved if k not in NAME_BEARING_FIELDS]:
            raise SystemExit(
                "restamp: %s changed OUTSIDE the name in its reviewed substance (%s changed, and only "
                "%s may). That is the safety envelope the reviewer judged, so no digest may certify "
                "it. Re-review it by hand."
                % (rel, moved, sorted(NAME_BEARING_FIELDS)))
        if not moved:
            continue
        p.write_text(REVIEWED_DIGEST_FIELD.sub(
            lambda m: m.group(1) + post_payload["digest"], post, count=1), "utf-8")
        out.append((rel, was, post_payload["digest"]))
        _follow_digest_references(dest, was, post_payload["digest"])
    return out


def _follow_digest_references(dest, was, now):
    """Carry every RECORDED REFERENCE to a re-stamped digest across with the content.

    A digest IS a content address, so a reference to it is a reference to that exact content, and a
    reference left pointing at the old address is now pointing at nothing. The suite that asserts
    over these examples holds the scale-pool digest as a literal inside a `.replace()` over the real
    shipped file: leave it behind and the replace silently no-ops, its guard turns red, and the fix
    trades three failures for a new one. Digests are unique enough to substitute by value.

    `_is_text` keeps this OUT of proof/, which is right and not an omission: a proof records the
    digest that was current when the evidence was recorded, and that reference is history."""
    moved = 0
    for rel in tracked_files(dest):
        p = Path(dest) / rel
        if not p.is_file() or not _is_text(rel):
            continue
        try:
            text = p.read_text("utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if was in text:
            p.write_text(text.replace(was, now), "utf-8")
            moved += 1
    if moved:
        print("    carried %d reference(s) from %s to %s" % (moved, was, now))
    return moved


def untracked_state_left_behind(dest):
    """Files still sitting under the OLD state directory after the move, which means untracked ones.

    `_move_paths` derives its work from `tracked_files`, so untracked local state under the state
    directory is invisible to it and stays where it was. That is not hypothetical: the live cutover
    left `.warp/trackers.json` behind, and because the projection code treats a missing config as
    "this repo is not wired for projection", the capability would have gone quietly rather than
    loudly. A silent loss is the worst outcome available here, so the migration says so. It does not
    move them: untracked state is the operator's, and some of it (bytecode caches) should just be
    deleted. Naming it is the job."""
    old_dir = Path(dest) / ".warp"
    if not old_dir.exists():
        return []
    return sorted(str(q.relative_to(dest)) for q in old_dir.rglob("*")
                  if q.is_file() and q.suffix != ".pyc")


def repin_file_digests(dest, sha_moves):
    """Move every PINNED sha256 of a file whose content the rename changed.

    A pin exists to redden the gate when a file is edited, and the rename IS an edit, so leaving the
    pin behind reports the rename as tampering. Moving it is only safe because it is CONTENT
    ADDRESSED: the substitution is keyed on the digest the file HAD, so a pin that matched this file
    before matches the same file after, and a digest that matched no file is not touched at all.

    Same principle as the action-review references, and the same reason it is sound: nothing here
    decides what a digest OUGHT to be, it only follows the content the digest already named."""
    out = []
    for was, now in sorted(sha_moves.items()):
        moved = 0
        for rel in tracked_files(dest):
            p = Path(dest) / rel
            if not p.is_file() or not _is_text(rel):
                continue
            try:
                text = p.read_text("utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if was in text:
                p.write_text(text.replace(was, now), "utf-8")
                moved += 1
        if moved:
            out.append((was, now, moved))
    return out


def _move_paths(dest, reverse, pairs=None):
    """Move every renamed path. On reverse, swap each pair and move back."""
    pairs = pairs if pairs is not None else path_renames(dest)
    for src, dst in pairs:
        a, b = (dst, src) if reverse else (src, dst)
        sp, dp = Path(dest) / a, Path(dest) / b
        if sp.exists():
            dp.parent.mkdir(parents=True, exist_ok=True)
            r = subprocess.run(["git", "-C", str(dest), "mv", a, b], capture_output=True)
            if sp.exists():
                shutil.move(str(sp), str(dp))
    return pairs


def migrate_tree(dest, reverse=False, manifest=None):
    """Migrate a COPY. Forward FILLS the manifest, reverse REPLAYS it.

    ORDER IS OPPOSITE IN THE TWO DIRECTIONS, and getting it wrong is a silent corruption rather
    than an error. Forward rewrites contents and THEN moves paths. Reverse must move paths BACK
    FIRST, because the manifest is keyed by the ORIGINAL relative path: after the forward move,
    `.warp/x.py` is on disk as `.veldo/x.py`, the lookup misses, and every file under the renamed
    directory is silently left un-reversed. That is what took the round trip from 39 mismatches to
    118 before the order was fixed."""
    if manifest is None:
        raise SystemExit("migrate_tree needs a manifest dict: forward FILLS it, reverse REPLAYS it")
    if reverse and not manifest:
        raise SystemExit("refusing to reverse without the forward manifest: on this repository the "
                         "transform is not injective, so a reverse that re-derives its own rules "
                         "corrupts every pre-existing mention of the target name")
    if reverse:
        _move_paths(dest, reverse=True, pairs=manifest.get("__paths__", []))

    changed = 0
    # THE PRE-RENAME TEXT IS THE ONLY EVIDENCE that a review was valid before we touched it, and it
    # is gone the moment the file is written. Captured here, on the forward pass, for restamp_reviews.
    reviewed = set(reviewed_artifacts(dest)) if not reverse else set()
    pre_texts, sha_moves = {}, {}
    for rel in tracked_files(dest):
        p = Path(dest) / rel
        if not p.is_file() or not _is_text(rel):
            continue
        try:
            before = p.read_text("utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if rel in reviewed:
            pre_texts[rel] = before
        if reverse:
            passes = manifest.get(rel) if rel != "__paths__" else None
            if not passes:
                continue
            after = rewrite_reverse(before, passes)
        else:
            after, passes = rewrite_forward(before)
            if any(passes):
                manifest[rel] = passes
        if after != before:
            if not reverse:
                sha_moves[hashlib.sha256(before.encode()).hexdigest()] = \
                    hashlib.sha256(after.encode()).hexdigest()
            p.write_text(after, "utf-8")
            changed += 1

    if not reverse:
        manifest["__paths__"] = _move_paths(dest, reverse=False)
        for _left in untracked_state_left_behind(dest):
            print("  WARNING: %s is UNTRACKED local state and was NOT migrated; the renamed code "
                  "reads the new path and will not find it" % _left)
        repinned = repin_file_digests(dest, sha_moves)
        for was, now, n in repinned:
            print("  re-pinned %s -> %s (%d reference(s))" % (was[:16], now[:16], n))
        manifest["__repinned__"] = [list(t) for t in repinned]
        stamped = restamp_reviews(dest, pre_texts, action_payload_reader(dest))
        for rel, was, now in stamped:
            print("  re-stamped review: %s  %s -> %s" % (rel, was, now))
        if stamped:
            print("re-stamped %d review(s), each proven valid before the rename and changed by the "
                  "rename ALONE" % len(stamped))
        manifest["__restamped__"] = [list(t) for t in stamped]
    return changed


def plan():
    """What would change, per surface, without writing anything."""
    counts, protected = {}, 0
    for rel in tracked_files(ROOT):
        p = ROOT / rel
        if not p.is_file() or not _is_text(rel):
            continue
        try:
            text = p.read_text("utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        masked, (_ids, _esc) = _mask_spec_ids(text)
        protected += len(_ids)
        for fwd_pat, _r, _a, _b in RULES:
            n = len(re.findall(fwd_pat, masked))
            if n:
                counts[fwd_pat] = counts.get(fwd_pat, 0) + n
    print("spec ids PROTECTED from every rule: %d" % protected)
    print("substitutions by rule, most specific first:")
    for fwd_pat, _r, _a, _b in RULES:
        if fwd_pat in counts:
            print("  %-42s %d" % (fwd_pat, counts[fwd_pat]))
    print("paths renamed on disk: %d" % len(path_renames(ROOT)))
    return 0


def verify(dest):
    """THE ROUND TRIP, which is the actual proof. Migrate a copy, reverse it FROM THE MANIFEST, and
    require every tracked file to come back byte-identical to this repository's."""
    d = Path(dest)
    if d.exists():
        shutil.rmtree(d)
    subprocess.run(["git", "clone", "-q", str(ROOT), str(d)], check=True)

    # SNAPSHOT THE CLONE, not this working tree. An earlier version compared the round-tripped
    # clone against ROOT's live files and reported two mismatches that were nothing to do with the
    # migration: the clone comes from HEAD, and the working tree had uncommitted edits plus a
    # gate-written ledger. The round trip has to be measured against its own starting point.
    before_digests = {rel: _digest(d / rel) for rel in tracked_files(d)
                      if (d / rel).is_file() and _is_text(rel)}

    manifest = {}
    fwd = migrate_tree(d, reverse=False, manifest=manifest)
    edits = sum(len(e) for passes in manifest.values() for e in passes)
    print("forward: %d file(s) rewritten, %d edit(s) recorded across %d file(s)"
          % (fwd, edits, len(manifest)))
    residual = subprocess.run(["git", "-C", str(d), "grep", "-il", "warp"],
                              capture_output=True, text=True).stdout.split()
    print("files still mentioning the old name after forward: %d" % len(residual))

    rev = migrate_tree(d, reverse=True, manifest=manifest)
    print("reverse: %d file(s) rewritten from the manifest" % rev)

    mismatched, checked = [], 0
    for rel, digest in before_digests.items():
        b = d / rel
        checked += 1
        if not b.is_file() or _digest(b) != digest:
            mismatched.append(rel)
    print("ROUND TRIP: %d file(s) compared, %d mismatched" % (checked, len(mismatched)))
    for rel in mismatched[:15]:
        print("   MISMATCH %s" % rel)
    return 1 if mismatched else 0


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--apply")
    ap.add_argument("--reverse")
    ap.add_argument("--verify")
    a = ap.parse_args(argv[1:])
    if a.plan:
        return plan()
    if a.verify:
        return verify(a.verify)
    for target, rev in ((a.apply, False), (a.reverse, True)):
        if target:
            if Path(target).resolve() == ROOT:
                print("refusing to migrate the live repository in place; pass a copy")
                return 2
            # A target that is not a git tree yields zero tracked files, so the run would report
            # "0 file(s) rewritten" and exit 0. That reads as success and is the opposite. Refuse.
            if not (Path(target) / ".git").exists():
                print("no git tree at %s. --apply migrates an EXISTING copy; it does not create "
                      "one. Clone first:\n  git clone -q %s %s" % (target, ROOT, target))
                return 2
            man_path = Path(target).parent / (Path(target).name + ".rename-manifest.json")
            if rev:
                man = json.loads(man_path.read_text())
                print("%d file(s) reversed from %s"
                      % (migrate_tree(Path(target), reverse=True, manifest=man), man_path))
            else:
                man = {}
                n = migrate_tree(Path(target), reverse=False, manifest=man)
                man_path.write_text(json.dumps(man))
                print("%d file(s) rewritten; manifest written to %s (KEEP IT: the reverse needs it)"
                      % (n, man_path))
            return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
