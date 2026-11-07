#!/usr/bin/env python3
"""VELDO-0272 AC4: the owner's daily summary of what landed.

The owner left the approval of routine work (Telegram 39707, 39708) on one condition: he sees, once a
day, everything that landed. For each landing the summary names the ticket, its title cut to one line,
the gate result at the landed commit, the reviewer of the verdict it landed on, and whether approval
was required and who approved. A day with no landings says so in one line. The counts (approval
required, not required) are the only metric.

TWO SOURCES, ONE FORMATTER. Until the factory runs, `python3 .veldo/landed_summary.py day YYYY-MM-DD`
reads the first-parent commits that reached main that day (by committer date), one landing per ticket
named in the commit subject (its newest commit that day is the landed commit), and that commit's spec,
proof bundle (verdicts, approvals) and gate events; it writes .veldo/runtime/landed/YYYY-MM-DD.md, which
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


def landing_at(root, ticket, commit):
    """One landing's fields, read from the committed files at `commit`."""
    fm = {}
    for name in _names(root, commit, "specs"):
        if name.startswith("specs/%s-" % ticket) and name.endswith(".md"):
            try:
                fm = _Y.front_matter(_show(root, commit, name) or "", name) or {}
            except ValueError:
                fm = {}
            break
    words = str(fm.get("human_approval", "not_required")).split()
    required = not (words and words[0] == "not_required")
    reviewer, approvers = NONE, []
    for name in _names(root, commit, "proof/%s" % ticket):
        leaf = name.rsplit("/", 1)[-1]
        data = _json(root, commit, name) if leaf.endswith(".json") else None
        if data is None:
            continue
        if leaf.startswith("verdict") and data.get("verdict") in ("pass", "pass_with_notes") and data.get("reviewer"):
            reviewer = str(data["reviewer"])
        if leaf.startswith("approval") and data.get("decision") == "approved" and data.get("approver"):
            approvers.append(str(data["approver"]))
    return {"ticket": ticket, "title": one_line(fm.get("title") or ""), "commit": commit,
            "gate": _gate(root, ticket, commit), "reviewer": reviewer,
            "approval_required": required, "approvers": sorted(set(approvers))}


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
        else:
            approval = "not required"
        lines.append("- %s %s | gate %s | reviewer %s | approval %s"
                     % (item["ticket"], item["title"], item["gate"], item["reviewer"], approval))
    return "\n".join(lines)


def landings_on(root, day, ref="main"):
    """The day's landings from the first-parent line of `ref`, oldest first."""
    newest = {}
    order = []
    for line in (_git(root, "log", "--first-parent", "--format=%H%x00%cs%x00%s", ref) or "").splitlines():
        sha, date, subject = (line.split("\0") + ["", ""])[:3]
        if date != day:
            continue
        found = TICKET.search(subject)
        if found and found.group(1) not in newest:
            newest[found.group(1)] = sha
            order.append(found.group(1))
    return [landing_at(root, ticket, newest[ticket]) for ticket in reversed(order)]


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
