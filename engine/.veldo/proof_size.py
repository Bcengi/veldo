"""VELDO contract validator, part three: proof is small summaries, never raw bulk (VELDO-0270).

Moved out of .veldo/validate.py unchanged, so validate.py stays inside its file_lines budget.
Loaded ONLY by validate.py, from beside itself, on first use (as it loads request.py): the
dependency is one-way (validate.py -> proof_size.py, never back). validate.py binds this
module's parse_yamlish and fail to its ONE front-matter parser and ONE failure reporter after
loading it and delegates the public names to it, so V.check_proof_files, V.write_proof_summary
and the rest resolve on validate.py exactly as before.
"""
import base64 as _b64
import fnmatch as _fnmatch
import importlib.util
import json
import os as _os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
parse_yamlish = None  # bound by validate.py
fail = None  # bound by validate.py


# ---------------------------------------------------------------------------------------------
# VELDO-0270: PROOF IS SMALL SUMMARIES, NEVER RAW BULK. One implementation of the rules, used by
# the contracts stage (run_all, mode proof-files) and by the push guard (mode push-proof), so the
# gate and the guard cannot disagree about the limit or about what an encoded archive is.
#   proof_file_over_limit    a tracked proof file larger than proof.max_file_bytes
#   proof_encoded_archive    base64 text decoding to an archive or compressed stream, any size
#   proof_reference_dangling a proof file still naming a removed file instead of its summary
#   proof_summary_incomplete a *.summary.json without its command, environment or discarded digests
# The limit is .veldo/policy.yaml key proof.max_file_bytes, default 1,048,576 bytes when the key
# is absent. A key that is present but not a positive integer is a refusal, never the default.
# ---------------------------------------------------------------------------------------------
_gp_spec = importlib.util.spec_from_file_location("validate_git_process", Path(__file__).with_name("git_process.py"))
_git_process = importlib.util.module_from_spec(_gp_spec)
_gp_spec.loader.exec_module(_git_process)

PROOF_LIMIT_DEFAULT = 1048576
PROOF_PROTECTED_REFS_DEFAULT = ["refs/heads/main", "refs/tags/*"]
SUMMARY_SCHEMA = "veldo.proof-summary/v1"
_B64_RUN = re.compile(rb"[A-Za-z0-9+/]{64,}(?:(?:\r?\n|\\n)[A-Za-z0-9+/]+)*={0,2}")
_B64_SEP = re.compile(rb"\r?\n|\\n")
_ARCHIVE_MAGIC = (
    (b"\x1f\x8b", "gzip"),
    (b"PK\x03\x04", "zip"),
    (b"PK\x05\x06", "zip"),
    (b"BZh", "bzip2"),
    (b"\xfd7zXZ\x00", "xz"),
    (b"\x28\xb5\x2f\xfd", "zstd"),
)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def proof_policy(root=None):
    """(limit, source, protected_refs, problems) read from <root>/.veldo/policy.yaml."""
    base = Path(root) if root else ROOT
    pfile = base / ".veldo" / "policy.yaml"
    problems = []
    limit, source = PROOF_LIMIT_DEFAULT, "the default; .veldo/policy.yaml key proof.max_file_bytes is absent"
    refs = list(PROOF_PROTECTED_REFS_DEFAULT)
    data = {}
    if pfile.is_file():
        try:
            data = parse_yamlish(pfile.read_text()) or {}
        except Exception as e:  # an unreadable policy is a refusal, never the default
            problems.append(f"{pfile}: unreadable ({e})")
            data = {}
    section = data.get("proof") if isinstance(data, dict) else None
    if section is not None and not isinstance(section, dict):
        problems.append(f".veldo/policy.yaml key proof is not a mapping: {section!r}")
        section = None
    section = section or {}
    if "max_file_bytes" in section:
        v = section["max_file_bytes"]
        if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
            problems.append(f".veldo/policy.yaml key proof.max_file_bytes is not a positive integer: {v!r}")
        else:
            limit, source = v, ".veldo/policy.yaml key proof.max_file_bytes"
    if "protected_refs" in section:
        v = section["protected_refs"]
        if not isinstance(v, list) or not v or not all(isinstance(x, str) and x for x in v):
            problems.append(f".veldo/policy.yaml key proof.protected_refs is not a list of refs: {v!r}")
        else:
            refs = list(v)
    return limit, source, refs, problems


def encoded_archives(name, data):
    """[(offset, kind)] for base64 text in data that decodes to an archive or compressed stream.
    A name ending .b64 or .base64 is one at offset 0 whatever it holds."""
    found = []
    if name.endswith(".b64") or name.endswith(".base64"):
        found.append((0, "base64 file name"))
    for m in _B64_RUN.finditer(data):
        text = _B64_SEP.sub(b"", m.group(0)[:1200]).rstrip(b"=")
        text = text[: (min(len(text), 360) // 4) * 4]
        try:
            raw = _b64.b64decode(text)
        except Exception:
            continue
        kind = next((k for magic, k in _ARCHIVE_MAGIC if raw.startswith(magic)), None)
        if kind is None and raw[257:262] == b"ustar":
            kind = "tar"
        if kind:
            found.append((m.start(), kind))
    return found


def _tracked_proof_files(base):
    try:
        out = _git_process.run(["git", "-C", str(base), "ls-files", "-z", "--", "proof"],
                              capture_output=True, check=True).stdout
        rels = [r for r in out.decode("utf-8", "surrogateescape").split("\0") if r]
    except Exception:
        rels = None
    if rels is None:
        pdir = base / "proof"
        rels = sorted(str(p.relative_to(base)) for p in pdir.rglob("*") if p.is_file()) if pdir.is_dir() else []
    return [r for r in rels if (base / r).is_file()]


def summary_problems(data):
    """What a proof summary (veldo.proof-summary/v1) lacks: the exact command, the environment,
    and for every discarded raw file its name, size in bytes and sha256."""
    probs = []
    if not isinstance(data, dict):
        return ["not a JSON object"]
    if data.get("schema") != SUMMARY_SCHEMA:
        probs.append(f"schema is not {SUMMARY_SCHEMA}")
    if not isinstance(data.get("command"), str) or not data.get("command").strip():
        probs.append("no command")
    env = data.get("environment")
    if not isinstance(env, dict) or not env:
        probs.append("no environment")
    disc = data.get("discarded")
    if not isinstance(disc, list):
        probs.append("no discarded list (an empty list when nothing was discarded)")
        disc = []
    for i, d in enumerate(disc):
        if not isinstance(d, dict) or not isinstance(d.get("name"), str) or not d.get("name"):
            probs.append(f"discarded[{i}] has no name")
            continue
        if not isinstance(d.get("bytes"), int) or isinstance(d.get("bytes"), bool) or d["bytes"] < 0:
            probs.append(f"discarded {d['name']} has no size in bytes")
        if not isinstance(d.get("sha256"), str) or not _HEX64.match(d["sha256"]):
            probs.append(f"discarded {d['name']} has no sha256")
    return probs


def _removed_by_summary(base, rels):
    """{original_path: summary_rel} for every summary whose original file is absent."""
    removed = {}
    present = set(rels)
    for r in rels:
        if not r.endswith(".summary.json"):
            continue
        try:
            data = json.loads((base / r).read_text())
        except Exception:
            continue
        orig = data.get("original_path") if isinstance(data, dict) else None
        if isinstance(orig, str) and orig.startswith("proof/") and orig not in present:
            removed[orig] = r
    return removed


def _ref_patterns(orig):
    """The ways a proof file names a removed file: its repository path, its path relative to its
    bundle directory (proof/<ID>/) for files inside that bundle, or its bare name for files in
    its own directory."""
    parts = orig.split("/")
    bundle = "/".join(parts[:2]) + "/"
    rel = "/".join(parts[2:])
    out = [(None, orig)]
    if rel:
        out.append((bundle, rel))
    if len(parts) > 3:
        out.append(("/".join(parts[:-1]) + "/", parts[-1]))
    return out


def check_proof_files(root=None, quiet=False):
    """The four VELDO-0270 refusals over every file tracked under proof/ in the tree at root."""
    base = Path(root) if root else ROOT
    limit, source, _refs, pol = proof_policy(base)
    errs = 0
    for p in pol:
        errs += fail("proof_policy_invalid", p)
    rels = _tracked_proof_files(base)
    largest = (0, None)
    removed = _removed_by_summary(base, rels)
    pats = []
    for orig in removed:
        for scope, text in _ref_patterns(orig):
            rx = re.compile(rb"(?<![A-Za-z0-9_.-])" + re.escape(text.encode()) + rb"(?![A-Za-z0-9_-])(?!\.summary\.json)(?!\.[A-Za-z0-9])")
            pats.append((scope, orig, rx))
    for r in rels:
        fp = base / r
        size = fp.stat().st_size
        if size > largest[0]:
            largest = (size, r)
        if not pol and size > limit:
            errs += fail("proof_file_over_limit", f"{r}: {size} bytes, limit {limit} bytes ({source})")
        data = fp.read_bytes()
        for off, kind in encoded_archives(r, data):
            errs += fail("proof_encoded_archive", f"{r}: base64 run at byte offset {off} decodes to {kind}")
        if r.endswith(".summary.json"):
            try:
                sdata = json.loads(data.decode("utf-8"))
            except Exception as e:
                sdata = None
                errs += fail("proof_summary_incomplete", f"{r}: not JSON ({e})")
            if sdata is not None:
                probs = summary_problems(sdata)
                if probs:
                    errs += fail("proof_summary_incomplete", f"{r}: " + "; ".join(probs))
            continue
        named = set()
        for scope, orig, rx in pats:
            if orig in named or (scope and not r.startswith(scope)):
                continue
            if rx.search(data):
                named.add(orig)
                errs += fail("proof_reference_dangling",
                             f"{r} names {orig}, which is absent; name {removed[orig]} instead")
    if not quiet:
        big = f"{largest[1]} {largest[0]} bytes" if largest[1] else "none"
        print(f"  proof files checked: {len(rels)}; largest: {big}; limit {limit} bytes ({source})")
    return errs


def _git(base, *args):
    return _git_process.run(["git", "-C", str(base), *args], capture_output=True, check=True).stdout


def check_push_proof(lines, remote="", root=None):
    """The push guard's half: every commit a push to a protected ref sends that the remote does
    not already have, judged by the same two rules with the same limit. lines are git's pre-push
    stdin: '<local ref> <local sha> <remote ref> <remote sha>'."""
    base = Path(root) if root else Path.cwd()
    limit, source, refs, pol = proof_policy(base)
    errs = 0
    for p in pol:
        errs += fail("proof_policy_invalid", p)
    if pol:
        return errs
    zero = "0" * 40
    for line in lines:
        f = line.split()
        if len(f) != 4:
            continue
        _lref, lsha, rref, rsha = f
        if set(lsha) == {"0"} or not any(_fnmatch.fnmatchcase(rref, pat) for pat in refs):
            continue
        excl = ["--not"]
        if rsha != zero and set(rsha) != {"0"}:
            try:
                _git(base, "cat-file", "-e", rsha + "^{commit}")
                excl.append(rsha)
            except Exception:
                pass
        excl.append(f"--remotes={remote}" if remote else "--remotes")
        commits = _git(base, "rev-list", "--reverse", lsha, *excl).decode().split()
        for c in commits:
            parents = _git(base, "rev-list", "--parents", "-n", "1", c).decode().split()[1:]
            if parents:
                diff = _git(base, "diff-tree", "-r", "-z", "--no-commit-id", "--diff-filter=ACMR",
                            parents[0], c)
            else:
                diff = _git(base, "diff-tree", "-r", "-z", "--root", "--no-commit-id",
                            "--diff-filter=ACMR", c)
            toks = diff.decode("utf-8", "surrogateescape").split("\0")
            i = 0
            while i < len(toks) - 1:
                meta = toks[i].split()
                if not meta:
                    i += 1
                    continue
                n = 3 if meta[-1][:1] in ("R", "C") else 2
                path = toks[i + n - 1]
                blob = meta[3] if len(meta) > 3 else ""
                i += n
                if not path.startswith("proof/") or not blob:
                    continue
                size = int(_git(base, "cat-file", "-s", blob).decode().strip())
                where = f"push to {rref}: commit {c} adds {path}"
                if size > limit:
                    errs += fail("proof_file_over_limit",
                                 f"{where}: {size} bytes, limit {limit} bytes ({source})")
                for off, kind in encoded_archives(path, _git(base, "cat-file", "blob", blob)):
                    errs += fail("proof_encoded_archive",
                                 f"{where}: base64 run at byte offset {off} decodes to {kind}")
    return errs


def proof_summary(command, deciding, discarded=(), root=None, timing=False, extra=None):
    """A veldo.proof-summary/v1 record: what a proof writer keeps instead of its raw output.
    discarded is [(name, raw_bytes)]; each is recorded by name, size and sha256 and then dropped.
    timing adds the host load, for results that are timing sensitive."""
    import hashlib as _hl
    import platform as _pf
    base = Path(root) if root else ROOT

    def _rev(spec):
        try:
            return _git(base, "rev-parse", spec).decode().strip()
        except Exception:
            return "unknown"
    try:
        gitv = _git_process.run(["git", "--version"], capture_output=True, text=True).stdout.strip()
    except Exception:
        gitv = "unknown"
    env = {"commit": _rev("HEAD"), "tree": _rev("HEAD^{tree}"), "host": _pf.node(),
           "python": _pf.python_version(), "git": gitv}
    if timing:
        try:
            env["load"] = list(_os.getloadavg())
        except (OSError, AttributeError):
            env["load"] = "unavailable"
    disc = []
    for name, raw in discarded:
        raw = raw.encode() if isinstance(raw, str) else bytes(raw)
        disc.append({"name": name, "bytes": len(raw), "sha256": _hl.sha256(raw).hexdigest()})
    rec = dict(extra or {})
    rec.update({"schema": SUMMARY_SCHEMA, "command": command, "environment": env,
                "discarded": disc, "deciding": deciding})
    return rec


def write_proof_summary(path, command, deciding, discarded=(), root=None, timing=False, extra=None):
    """Write proof_summary(...) to path and return it. The summary itself must be under the
    policy limit; one that is not is a writer bug and raises rather than landing raw bulk."""
    rec = proof_summary(command, deciding, discarded, root, timing, extra)
    text = json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=True) + "\n"
    limit = proof_policy(root)[0]
    if len(text.encode()) > limit:
        raise ValueError(f"proof summary {path} is {len(text.encode())} bytes, over the limit {limit}")
    Path(path).write_text(text)
    return rec


def _short(value, n=400):
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True, default=str)
    return text if len(text) <= n else text[:n] + "..."


def summarize_mutation_receipt(receipt):
    """The deciding part of a mutation stage receipt (veldo.mutation-stage/v1): its counts, per case
    the expected and observed verdict, the detail of each case that did not go as expected, and
    the sha256 of the full result array, which is discarded."""
    import hashlib as _hl
    results = receipt.get("results") or []
    rows = []
    for r in results:
        case = r.get("case") or {}
        rows.append({"case": case.get("name") or case.get("identity"), "expected": "killed",
                     "observed": "killed", "source": r.get("source")})
    for r in receipt.get("invalid_results") or []:
        case = r.get("case") or {}
        rows.append({"case": case.get("name") or case.get("identity"), "expected": "killed",
                     "observed": r.get("error") or "invalid", "red": _short(r.get("detail"))})
    body = json.dumps(results, sort_keys=True, separators=(",", ":")).encode()
    counts = {k: receipt.get(k) for k in ("status", "registered", "executed", "reused", "rejected",
                                         "worker_invocations", "elapsed", "error") if k in receipt}
    return {"counts": counts, "rows": rows, "results_count": len(results),
            "results_sha256": _hl.sha256(body).hexdigest()}


_STAGE_LINE = re.compile(r"^   ([a-z][a-z _.-]*(?:: [a-z]+ leg)?): (pass|PASS|FAIL|fail|skip|SKIP|not-applicable)\b"
                         r"(?: \(([\d.]+)s\))?\s*$")
_NODE_LINE = re.compile(r"^node (\S+) end [\d.]+ (\S+) ([\d.]+)s")


def summarize_gate_transcript(text):
    """The stage table of a scripts/verify.sh transcript: each stage's verdict and seconds, the
    final GATE line, and the first failing row's detail. The transcript itself is discarded."""
    stages, nodes, first_fail = [], [], None
    for line in text.splitlines():
        m = _STAGE_LINE.match(line)
        if m:
            stages.append({"stage": m.group(1), "verdict": m.group(2),
                           "seconds": float(m.group(3)) if m.group(3) else None})
            continue
        m = _NODE_LINE.match(line)
        if m:
            nodes.append({"node": m.group(1), "verdict": m.group(2), "seconds": float(m.group(3))})
            continue
        if first_fail is None and re.search(r"\bFAIL\b", line):
            first_fail = line.strip()[:400]
    gate = [l.strip() for l in text.splitlines() if l.startswith("GATE:")]
    return {"gate": gate[-1] if gate else None, "stages": stages, "nodes": nodes,
            "first_failing_row": first_fail}


def write_gate_summary(transcript, out, command="bash scripts/verify.sh", root=None):
    """The gate transcript capture for proof: the stage table, never the transcript."""
    raw = Path(transcript).read_bytes()
    return write_proof_summary(out, command, summarize_gate_transcript(raw.decode("utf-8", "replace")),
                               discarded=[(Path(transcript).name, raw)], root=root, timing=True)
