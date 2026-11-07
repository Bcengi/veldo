#!/usr/bin/env python3
"""VELDO-0272 AC4: the owner's daily summary of what landed.

The owner left the approval of routine work (Telegram 39707, 39708) on one condition: he sees, once a
day, everything that landed. For each landing the summary names the ticket, its title cut to one line,
the gate result at the landed commit, the reviewer of the verdict it landed on, and whether approval
was required and who approved. A day with no landings says so in one line. The counts (approval
required, not required) are the only metric.

TWO SOURCES, ONE FORMATTER. Until the factory runs, `python3 .veldo/landed_summary.py day YYYY-MM-DD`
reads EVERY first-parent commit that reached main that day (by committer date): one landing per ticket
named in the commit subject (its newest commit that day is the landed commit), and each merge or commit
naming no ticket listed under its own subject; and the landed commit's spec, proof bundle (verdicts,
approvals) and gate events, judged by policy_check's own rule and review predicate; it writes .veldo/runtime/landed/YYYY-MM-DD.md, which
the assistant sends. Once the factory runs, control_telegram_report's daily_landed event feeds the day's
spec.shipped records to from_shipped and the same format_day, so the file and the message cannot
differ. Both read a landing through landing_at.

Read only: Git objects and the committed files at the landed commit. Standard library only.
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TICKET = re.compile(r"\b((?:VELDO|WARP)-\d{4,})\b")
TITLE_WIDTH = 100
NONE = "none"


def _sibling(name):
    spec = importlib.util.spec_from_file_location("veldo_landed_" + name, Path(__file__).resolve().with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_Y = _sibling("yamlish")
_G = _sibling("git_process")


def _git(root, *args):
    r = _G.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=300)
    return r.stdout if r.returncode == 0 else None


def _show(root, commit, rel):
    return _git(root, "show", "%s:%s" % (commit, rel))


def _names(root, commit, directory):
    out = _git(root, "ls-tree", "--name-only", commit, directory.rstrip("/") + "/")
    return sorted(out.splitlines()) if out else []


def one_line(text, width=TITLE_WIDTH):
    """A title cut to one line: whitespace collapsed, and cut at `width` with "..."."""
    flat = " ".join(str(text or "").split())
    return flat if len(flat) <= width else flat[:width - 3].rstrip() + "..."


def _json(root, commit, rel):
    try:
        data = json.loads(_show(root, commit, rel) or "")
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _gate(root, ticket, commit):
    """The newest gate event at the landed commit naming the landed commit or an earlier commit of the
    same ticket on its first-parent line: "green at <commit>", "red at <commit>", or none."""
    ours = set()
    for line in (_git(root, "log", "--first-parent", "--format=%H %s", commit) or "").splitlines():
        sha, _, subject = line.partition(" ")
        if ticket in TICKET.findall(subject):
            ours.add(sha)
    found = NONE
    for line in (_show(root, commit, ".veldo/events.jsonl") or "").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict) or event.get("type") not in ("gate.passed", "gate.failed"):
            continue
        if event.get("commit") in ours:
            found = "%s at %s" % ("green" if event["type"] == "gate.passed" else "red", event["commit"][:12])
    return found


def _policy_check():
    """The approval rule and the review predicate, from policy_check beside this file, so the summary
    shows the flag and the reviewer the push check computes, never a second reading of them."""
    return _sibling("policy_check")


def _patterns_at(root, commit):
    """The protected patterns of the policy committed at `commit`, or None when they cannot be read."""
    try:
        rows = _Y.parse(_show(root, commit, ".veldo/policy.yaml") or "").get("protected_paths")
    except Exception:
        return None
    if not isinstance(rows, list) or any(not isinstance(r, dict) or not isinstance(r.get("path"), str) for r in rows):
        return None
    return [r["path"] for r in rows]


def _subject(root, commit):
    return (_git(root, "log", "-1", "--format=%s", commit) or "").strip()


def _first_id(subject):
    found = TICKET.search(subject or "")
    return found.group(1) if found else None


def landing_range(root, ticket, commit):
    """The commits a landing brought: from `commit` back along the first-parent line while the subject
    names `ticket` first (one push of that ticket's commits), with every commit a merge among them
    brought in. A commit is credited to a ticket only by an id its subject names."""
    base = None
    for line in (_git(root, "log", "--first-parent", "--format=%H%x00%s", commit) or "").splitlines():
        sha, _, subject = line.partition("\0")
        if ticket is None and sha != commit or ticket is not None and _first_id(subject) != ticket:
            base = sha
            break
    out = _git(root, "rev-list", commit, *(["^" + base] if base else [])) or ""
    return [c for c in out.splitlines() if c] or [commit], base


def _touched(root, commit, base):
    out = _git(root, "diff", "--name-only", "--no-renames", base, commit) if base else \
        _git(root, "ls-tree", "-r", "--name-only", commit)
    return None if out is None else [f for f in out.splitlines() if f]


def _bundle(root, commit, ticket):
    """{leaf: parsed json} of proof/<ticket>/ at `commit`."""
    out = {}
    for name in _names(root, commit, "proof/%s" % ticket):
        leaf = name.rsplit("/", 1)[-1]
        if leaf.endswith(".json"):
            data = _json(root, commit, name)
            if data is not None:
                out[leaf] = data
    return out


def _bound(value, commits):
    return isinstance(value, str) and bool(value) and any(c.startswith(value) for c in commits)


def _judged_reviewer(P, ticket, bundle, commits):
    """The reviewer of the verdict the push check would accept for this landing (VELDO-0272 AC3 b):
    pass or pass_with_notes, no blocking findings, this spec, bound to a commit of the landing and to
    the proof digest at the landed commit, from a reviewer who is not the producer; else none."""
    manifest = bundle.get("manifest.json")
    if not manifest:
        return NONE
    producer = manifest.get("producer", "")
    for leaf in sorted(bundle, reverse=True):
        v = bundle[leaf]
        if not leaf.startswith("verdict") or v.get("verdict") not in ("pass", "pass_with_notes"):
            continue
        if P.blocking_findings(v) or v.get("spec_id") != ticket or not _bound(v.get("commit"), commits):
            continue
        if v.get("proof_digest") != P.proof_digest(manifest) or P._self_review(v.get("reviewer"), producer):
            continue
        return one_line(v["reviewer"] if isinstance(v.get("reviewer"), str) else json.dumps(v.get("reviewer"), sort_keys=True))
    return NONE


def _approvers(root, commit, tickets, commits):
    """Every approver of an approved record bound to a commit of the landing: in the named tickets'
    bundles, or, when the landing names none, in every bundle at the landed commit."""
    if tickets:
        names = [n for t in tickets for n in _names(root, commit, "proof/%s" % t)]
    else:
        names = (_git(root, "ls-tree", "-r", "--name-only", commit, "proof/") or "").splitlines()
    out = set()
    for name in names:
        if not name.rsplit("/", 1)[-1].startswith("approval") or not name.endswith(".json"):
            continue
        data = _json(root, commit, name)
        scope = data.get("scope") if data else None
        if data and data.get("decision") == "approved" and data.get("approver") and isinstance(scope, dict) \
                and _bound(scope.get("commit"), commits):
            out.add(str(data["approver"]))
    return sorted(out)


def _gate_at(root, commit, commits):
    found = NONE
    for line in (_show(root, commit, ".veldo/events.jsonl") or "").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict) or event.get("type") not in ("gate.passed", "gate.failed"):
            continue
        if event.get("commit") in commits:
            found = "%s at %s" % ("green" if event["type"] == "gate.passed" else "red", event["commit"][:12])
    return found


def landing_at(root, ticket, commit, label=None):
    """One landing's fields, read from the committed files at `commit`. `ticket` is the id the landed
    commit's subject names, or None for a commit that names none or a merge (listed under `label`, its
    subject). VELDO-0272 F4: the approval flag is the COMPUTED one (policy_check.effective_flag with the
    policy at that commit, or required when the landing touched a protected path or either cannot be
    read: fail closed), approvers are listed whenever an approved record binds to the landing, and the
    reviewer is the one of the verdict the push check would accept."""
    P = _policy_check()
    commits, base = landing_range(root, ticket, commit)
    pats = _patterns_at(root, commit)
    tickets = [ticket] if ticket else sorted(set(TICKET.findall(label or "")))
    required = pats is None
    title = one_line(label or "")
    reviewers = []
    for tid in tickets:
        fm = {}
        for name in _names(root, commit, "specs"):
            if name.startswith("specs/%s-" % tid) and name.endswith(".md"):
                try:
                    fm = _Y.front_matter(_show(root, commit, name) or "", name) or {}
                except ValueError:
                    fm = {}
                break
        if ticket and label is None:
            title = one_line(fm.get("title") or "")
        if pats is not None and P.effective_flag(fm, pats) == "required":
            required = True
        reviewer = _judged_reviewer(P, tid, _bundle(root, commit, tid), commits)
        if reviewer != NONE:
            reviewers.append(reviewer)
    touched = _touched(root, commit, base)
    if touched is None or (pats is not None and any(P.glob_covers(f, pat) for f in touched for pat in pats)):
        required = True
    if ticket and label is None:
        gate = _gate(root, ticket, commit)
    else:
        gate = _gate_at(root, commit, commits)
    return {"ticket": ticket if ticket and label is None else commit[:12], "title": title, "commit": commit,
            "gate": gate, "reviewer": ", ".join(reviewers) or NONE,
            "approval_required": required, "approvers": _approvers(root, commit, tickets, commits)}


def format_day(day, landings):
    """THE ONE FORMATTER: the file and the daily_landed message are this text, byte for byte."""
    if not landings:
        return "Veldo landed on %s: nothing landed." % day
    required = sum(1 for item in landings if item["approval_required"])
    lines = ["Veldo landed on %s: %d (approval required %d, not required %d)"
             % (day, len(landings), required, len(landings) - required)]
    for item in landings:
        if item["approval_required"]:
            approval = "required, approved by %s" % (", ".join(item["approvers"]) or "nobody recorded")
        elif item["approvers"]:
            approval = "not required, approved by %s" % ", ".join(item["approvers"])
        else:
            approval = "not required"
        lines.append("- %s %s | gate %s | reviewer %s | approval %s"
                     % (item["ticket"], item["title"], item["gate"], item["reviewer"], approval))
    return "\n".join(lines)


def landings_on(root, day, ref="main"):
    """EVERY landing of the day on the first-parent line of `ref` (VELDO-0272 F3), oldest first: the
    commits whose subject names a ticket id, one landing per ticket (its newest commit that day is the
    landed commit), and each other first-parent commit, a merge or a commit naming no ticket, listed
    under its own subject."""
    seen = set()
    items = []
    for line in (_git(root, "log", "--first-parent", "--format=%H%x00%cs%x00%P%x00%s", ref) or "").splitlines():
        sha, date, parents, subject = (line.split("\0") + ["", "", ""])[:4]
        if date != day:
            continue
        ticket = _first_id(subject)
        if len(parents.split()) > 1 or ticket is None:
            items.append((None, sha, subject))
        elif ticket not in seen:
            seen.add(ticket)
            items.append((ticket, sha, None))
    return [landing_at(root, ticket, sha, label) for ticket, sha, label in reversed(items)]


def from_shipped(root, shipped):
    """The factory path: the day's spec.shipped records, each naming its ticket (spec, else unit) and
    landed commit, read through the same landing_at."""
    out = []
    for event in shipped:
        ticket = event.get("spec") or event.get("unit")
        if ticket and event.get("commit"):
            out.append(landing_at(root, str(ticket), str(event["commit"])))
    return out


def write_day(root, day, ref="main"):
    text = format_day(day, landings_on(root, day, ref))
    target = Path(root) / ".veldo" / "runtime" / "landed" / ("%s.md" % day)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    return target, text


def main(argv):
    if len(argv) not in (2, 4) or argv[0] != "day" or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", argv[1]) \
            or (len(argv) == 4 and argv[2] != "--ref"):
        print("usage: landed_summary.py day YYYY-MM-DD [--ref REF]")
        return 2
    target, text = write_day(ROOT, argv[1], argv[3] if len(argv) == 4 else "main")
    print(text)
    print("written: %s" % target)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
