"""Required-evidence debt ratchet. The strict predicate remains owned by validate.py."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path

REGISTER = ".veldo/required-evidence-debt.jsonl"


def pairs(validator, root):
    by_id = {}
    for path in sorted((root / "specs").glob("*.md")):
        if path.name == "index.md" or path.name.startswith("TEMPLATE"):
            continue
        fm = validator.front_matter(path.read_text())
        if fm and fm.get("id"):
            if fm["id"] in by_id:
                raise ValueError("duplicate spec id: " + fm["id"])
            by_id[fm["id"]] = path
    result = []
    for proof in validator._CORPUS.corpus_in_dir(root / "proof", validator._CORPUS.MANIFEST_PATTERN):
        sid = json.loads(proof.read_text()).get("spec_id")
        if sid in by_id:
            result.append((by_id[sid], proof))
    return result


def compute(validator, root, matched):
    """One line per failing pair, with the strict predicate's actual causes."""
    rows = []
    for spec, proof in matched:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            errors = validator.check_required_evidence(spec, proof)
        if errors:
            causes = [line.strip().replace(str(root) + "/", "")
                      for line in output.getvalue().splitlines()]
            rows.append({"spec": spec.relative_to(root).as_posix(),
                         "proof": proof.relative_to(root).as_posix(), "causes": causes})
    return sorted(rows, key=lambda row: (row["spec"], row["proof"]))


def render(rows):
    return "".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in rows)


def push_context(root):
    """Use the gate policy's existing range order and Git subprocess boundary."""
    loader = importlib.util.spec_from_file_location(
        "evidence_debt_policy", Path(__file__).with_name("policy_check.py"))
    policy = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(policy)
    policy.ROOT = root
    _git_process = policy._git_process

    def git(*args):
        return _git_process.run(["git", *args], cwd=root, text=True, capture_output=True)

    for push_range in policy._range_specs():
        changed = git("diff", "--name-only", "--no-renames", "-z", push_range)
        if changed.returncode:
            continue
        base = push_range.rsplit("..", 1)[0]
        # Resolve once: all historical register reads use this exact commit.
        resolved = git("rev-parse", "--verify", base + "^{commit}")
        if resolved.returncode:
            raise ValueError("cannot resolve required-evidence debt base")
        base = resolved.stdout.strip()
        present = git("ls-tree", base, "--", REGISTER)
        if present.returncode:
            raise ValueError("cannot inspect push-base debt register")
        previous = None
        if present.stdout:
            content = git("show", base + ":" + REGISTER)
            if content.returncode:
                raise ValueError("cannot read push-base debt register")
            previous = content.stdout
        return set(filter(None, changed.stdout.split("\0"))), previous
    raise ValueError("cannot resolve push range for required-evidence debt; no exemption granted")


def check(validator, root, rows, changed, previous):
    """Check exact computed debt, touched-pair refusals, and monotonic membership."""
    path = root / REGISTER
    actual = path.read_text() if path.exists() else ""
    expected = render(rows)
    errs = 0
    if actual != expected:
        errs += validator.fail(path, "debt register differs from computed strict failures; "
                               "run python3 .veldo/validate.py evidence-debt and review the diff "
                               "(remove passing entries; no missing or hand-added entries)")
    if previous is not None and not path.exists():
        errs += validator.fail(path, "adopted debt register missing; retain the empty register after payoff")
    if previous is not None:
        old_rows = [json.loads(line) for line in previous.splitlines()]
        old_pairs = {(row["spec"], row["proof"]) for row in old_rows}
        for row in rows:
            if (row["spec"], row["proof"]) not in old_pairs:
                errs += validator.fail(path, "new required-evidence debt forbidden: " + row["proof"])
    for row in rows:
        proof_dir = str(Path(row["proof"]).parent) + "/"
        touched = row["spec"] in changed or any(p.startswith(proof_dir) for p in changed)
        if touched:
            errs += validator.fail(row["proof"], "touched pair requires passing evidence: "
                                   + "; ".join(row["causes"]))
    return errs


def validate(validator, root, matched):
    rows = compute(validator, root, matched)
    try:
        changed, previous = push_context(root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        # No exemption is needed by a debt-free fresh adopter, including non-Git
        # CLI fixtures. When a range exists, still check its adoption boundary.
        if not rows and not (root / REGISTER).exists():
            return 0
        for row in rows:
            for cause in row["causes"]:
                validator.fail(REGISTER, cause)
        return validator.fail(REGISTER, str(exc))
    try:
        return check(validator, root, rows, changed, previous)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return validator.fail(REGISTER, str(exc))
