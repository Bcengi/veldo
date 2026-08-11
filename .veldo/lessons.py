#!/usr/bin/env python3
"""VELDO lessons store: capture failure modes and surface the relevant ones.

What broke once should be checked next time. This is the durable, cross-
iteration memory of failure: a small append-only store of lessons (a bug class,
a regression, a review finding, an emergency) and a way to SURFACE only the
lessons whose scope matches the change under review, so an unrelated lesson is
not put in front of a reviewer and a relevant one is never missed.

Two mechanical parts live here; the surfacing itself is a review-skill
procedure (see packs/claude/skills/review/SKILL.md):

  add(lesson)          validate the envelope and append it to .veldo/lessons.jsonl;
                       an unknown category, an empty text, or a malformed scope
                       is a named LessonError and is NOT stored.
  relevant(context)    the lessons whose scope matches a context (touched paths,
                       a plan id, or spec tags), most-recent-first. A context
                       that matches nothing returns []: relevant() filters, it
                       does not pass everything through.

A lesson envelope (schema veldo.lesson/v1):
  {id, created_at, category, scope, text, source}
where scope is exactly one of {"path": <glob>} (matched against touched paths)
or {"tag": <id>} (matched against the context plan id or its tags), and source
is the spec id or verdict that taught the lesson (optional).

CLI (for the review skill and for hand use):
  python3 .veldo/lessons.py add --category review_finding \\
      --path "scripts/**" --text "prove each assertion can fail" --source WARP-0001
  python3 .veldo/lessons.py relevant --path scripts/selftest.py --plan PLAN-0004
  python3 .veldo/lessons.py list

No state of its own beyond the jsonl file; the file is the truth.
"""
import argparse
import datetime
import fnmatch
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LESSONS = ROOT / ".veldo" / "lessons.jsonl"

SCHEMA = "veldo.lesson/v1"

# The fixed category vocabulary: the kinds of failure worth remembering. Adding
# a category is a conscious contract change, not an ad-hoc string, so a typo is
# a rejected lesson rather than a silently mis-filed one.
CATEGORIES = {"bug_class", "regression", "review_finding", "emergency"}


class LessonError(ValueError):
    """A lesson that does not satisfy the envelope contract.

    Named (and a ValueError subclass) so a caller distinguishes a bad lesson
    from any other error and never stores it. A malformed lesson is loud, not
    silently dropped into the store.
    """


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_scope(scope):
    """A scope is exactly one of {'path': glob} or {'tag': id}, value non-empty."""
    if not isinstance(scope, dict):
        raise LessonError("scope must be a mapping with exactly one of 'path' or 'tag'")
    keys = set(scope)
    if keys not in ({"path"}, {"tag"}):
        raise LessonError(
            "scope must have exactly one of 'path' (a glob) or 'tag' (a plan or spec id), "
            "got keys: %s" % sorted(keys))
    (key,) = keys
    val = scope[key]
    if not isinstance(val, str) or not val.strip():
        raise LessonError("scope %s must be a non-empty string" % key)
    return {key: val.strip()}


def make_lesson(category, scope, text, source=None):
    """Validate the parts and return a complete envelope, or raise LessonError.

    Pure: it touches no file. add() persists what this returns.
    """
    if category not in CATEGORIES:
        raise LessonError("unknown category %r (allowed: %s)" % (category, sorted(CATEGORIES)))
    if not isinstance(text, str) or not text.strip():
        raise LessonError("lesson text must be a non-empty string")
    if source is not None and (not isinstance(source, str) or not source.strip()):
        raise LessonError("source, when present, must be a non-empty string")
    lesson = {
        "schema": SCHEMA,
        "id": uuid.uuid4().hex[:12],
        "created_at": now_iso(),
        "category": category,
        "scope": _validate_scope(scope),
        "text": text.strip(),
    }
    if source:
        lesson["source"] = source.strip()
    return lesson


def add(lesson, store=LESSONS):
    """Validate a lesson mapping and append it to the store; return the envelope.

    Raises LessonError (and stores nothing) on an unknown category, an empty or
    missing text, or a malformed scope. A caller-supplied id or created_at is
    honored when valid (so a lesson can be replayed deterministically), otherwise
    a fresh one is minted.
    """
    if not isinstance(lesson, dict):
        raise LessonError("lesson must be a mapping")
    env = make_lesson(
        category=lesson.get("category"),
        scope=lesson.get("scope"),
        text=lesson.get("text"),
        source=lesson.get("source"),
    )
    if isinstance(lesson.get("id"), str) and lesson["id"].strip():
        env["id"] = lesson["id"].strip()
    if isinstance(lesson.get("created_at"), str) and lesson["created_at"].strip():
        env["created_at"] = lesson["created_at"].strip()
    store = Path(store)
    store.parent.mkdir(parents=True, exist_ok=True)
    with open(store, "a") as f:
        f.write(json.dumps(env) + "\n")
    return env


def load(store=LESSONS):
    """Every stored lesson, in append order. Blank or unparseable lines are
    skipped defensively (add() is the only sanctioned writer, so this is a
    read-robustness measure, not a validation seam)."""
    store = Path(store)
    out = []
    if not store.exists():
        return out
    for line in store.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def scope_matches(scope, context):
    """Does this lesson's scope match the change context? Pure predicate.

    context keys (all optional): paths (list of touched paths), plan (a plan id),
    tags (a list of spec or plan tags). A path scope matches if any touched path
    matches its glob; a tag scope matches the plan id or one of the tags. Case is
    significant (fnmatchcase) so matching is deterministic across platforms.
    """
    context = context or {}
    if not isinstance(scope, dict):
        return False
    if "path" in scope:
        glob = scope["path"]
        return any(fnmatch.fnmatchcase(p, glob) for p in (context.get("paths") or []))
    if "tag" in scope:
        tag = scope["tag"]
        if tag == context.get("plan"):
            return True
        return tag in (context.get("tags") or [])
    return False


def relevant(context, store=LESSONS, lessons=None):
    """The lessons whose scope matches the context, most-recent-first.

    Most-recent-first = created_at descending, later-appended breaking ties, so
    the freshest lesson for a scope is surfaced first. An unrelated lesson is
    excluded; an empty store (or a context that matches nothing) returns []."""
    items = lessons if lessons is not None else load(store)
    matched = [l for l in items if scope_matches(l.get("scope"), context)]
    return [l for _, l in sorted(
        list(enumerate(matched)),
        key=lambda il: (il[1].get("created_at", ""), il[0]),
        reverse=True,
    )]


def main():
    ap = argparse.ArgumentParser(
        description="VELDO lessons store: capture failure modes and surface the relevant ones.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="append a lesson")
    a.add_argument("--category", required=True, help="one of: %s" % sorted(CATEGORIES))
    g = a.add_mutually_exclusive_group(required=True)
    g.add_argument("--path", help="a path glob this lesson is scoped to")
    g.add_argument("--tag", help="a plan or spec id this lesson is scoped to")
    a.add_argument("--text", required=True, help="what to check next time")
    a.add_argument("--source", help="the spec id or verdict that taught it")

    r = sub.add_parser("relevant", help="surface the lessons relevant to a context")
    r.add_argument("--path", action="append", default=[], help="a touched path (repeatable)")
    r.add_argument("--plan", help="the change's plan id")
    r.add_argument("--tag", action="append", default=[], help="a spec or plan tag (repeatable)")
    r.add_argument("--json", action="store_true", help="machine-readable output")

    sub.add_parser("list", help="print every stored lesson")

    args = ap.parse_args()
    if args.cmd == "add":
        scope = {"path": args.path} if args.path else {"tag": args.tag}
        try:
            env = add({"category": args.category, "scope": scope,
                       "text": args.text, "source": args.source})
        except LessonError as ex:
            print("lesson rejected: %s" % ex)
            return 2
        print(json.dumps(env))
        return 0
    if args.cmd == "relevant":
        ctx = {"paths": args.path, "plan": args.plan, "tags": args.tag}
        hits = relevant(ctx)
        if args.json:
            print(json.dumps(hits, indent=2))
            return 0
        if not hits:
            print("(no relevant lessons for this context)")
            return 0
        print("Relevant lessons (check these):")
        for l in hits:
            src = (" [%s]" % l.get("source")) if l.get("source") else ""
            print("  - (%s) %s%s" % (l.get("category"), l.get("text"), src))
        return 0
    if args.cmd == "list":
        for l in load():
            print(json.dumps(l))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
