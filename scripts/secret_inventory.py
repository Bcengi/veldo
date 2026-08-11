#!/usr/bin/env python3
"""Run the secret inventory over a repository: working tree AND reachable history.

    python3 scripts/secret_inventory.py [--json] [repo_root]

The git plumbing lives here and the decisions live in `.veldo/secret_inventory.py`, so the module
stays pure and testable with a fake history while this side does the reading. Prints findings BY
REFERENCE - path, line, detector, digest - and never the matched text.

Exit code is 1 only when the declared posture is enforcing AND something is outstanding. Advisory
reports and returns 0, which is D4's sequencing: no repository is blocked on day one.
"""
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

MAX_BLOB = 2_000_000        # a blob larger than this is a binary or a dataset, not a config file


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _git(root, *args):
    return subprocess.run(["git", "-C", str(root)] + list(args),
                          capture_output=True, text=True).stdout


def digest_of(text):
    """Identify a line without disclosing it. Truncated because this is an identity, not a proof."""
    return "sha256:" + hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:12]


def working_tree(root):
    """Every TRACKED file. Untracked files are not in the repository and an ignored one is a local
    concern; scanning them would report a developer's own .env as a repository finding."""
    files = {}
    for rel in _git(root, "ls-files", "-z").split("\0"):
        if not rel:
            continue
        path = root / rel
        try:
            if path.stat().st_size > MAX_BLOB:
                continue
            files[rel] = path.read_text("utf-8", "replace")
        except (OSError, UnicodeError):
            continue
    return files


def reachable_blobs(root):
    """Every blob reachable from any ref, with the path it was last seen at.

    THIS IS THE HALF THAT MATTERS. A credential committed and deleted is still in every clone."""
    paths = dict(l.split(" ", 1) for l in _git(root, "rev-list", "--objects", "--all").splitlines()
                 if " " in l)
    if not paths:
        return []
    check = subprocess.run(
        ["git", "-C", str(root), "cat-file",
         "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
        input="\n".join(paths), capture_output=True, text=True).stdout.splitlines()
    shas = [w[0] for w in (l.split() for l in check)
            if len(w) == 3 and w[1] == "blob" and int(w[2]) < MAX_BLOB]
    if not shas:
        return []
    buf = subprocess.run(["git", "-C", str(root), "cat-file", "--batch"],
                         input="\n".join(shas).encode(), capture_output=True).stdout
    out, pos = [], 0
    while pos < len(buf):
        nl = buf.index(b"\n", pos)
        head = buf[pos:nl].decode().split()
        if len(head) != 3:
            break
        size = int(head[2])
        out.append((head[0], paths.get(head[0], "?"),
                    buf[nl + 1:nl + 1 + size].decode("utf-8", "replace")))
        pos = nl + 1 + size + 1
    return out


def main(argv):
    as_json = "--json" in argv
    rest = [a for a in argv[1:] if not a.startswith("--")]
    root = Path(rest[0] if rest else Path(__file__).resolve().parent.parent)
    inv = _load("veldo_secret_inventory", root / ".veldo/secret_inventory.py")
    scan = _load("veldo_secret_scan", root / ".veldo/secret_scan.py")

    findings = (inv.scan_tree(working_tree(root), scan, digest_of)
                + inv.scan_history(reachable_blobs(root), scan, digest_of))

    record_path = root / ".veldo/secret_inventory.json"
    record = json.loads(record_path.read_text()) if record_path.exists() else {}
    result = inv.gate_result(findings, record.get("declaration"), record.get("dispositions"))
    triaged = inv.triage(findings, record.get("dispositions"))

    if as_json:
        print(json.dumps({"result": result, "outstanding": triaged["outstanding"],
                          "rotation": inv.rotation_worklist(triaged["outstanding"],
                                                            record.get("owners"))}, indent=2))
    else:
        for line in inv.report(result, triaged["outstanding"]):
            print(line)
        for item in inv.rotation_worklist(triaged["outstanding"], record.get("owners")):
            print("  ROTATE %s %s -> %s" % (item["detector"], item["digest"], item["owner"]))
    return 1 if result["blocks"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
