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


def push_context(root, policy=None):
    """Resolve one trunk ancestor, using the policy's explicit BASE when supplied."""
    if policy is None:
        loader = importlib.util.spec_from_file_location(
            "evidence_debt_policy", Path(__file__).with_name("policy_check.py"))
        policy = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(policy)
    _git_process = policy._git_process

    def git(*args):
        return _git_process.run(["git", *args], cwd=root, text=True, capture_output=True)

    prefix_result = git("rev-parse", "--show-prefix")
    if prefix_result.returncode:
        raise ValueError("cannot resolve VELDO root prefix")
    prefix = prefix_result.stdout.rstrip("\n")
    refs = [str(policy.BASE)] if policy.BASE is not None else ["origin/HEAD", "origin/main"]
    for ref in refs:
        resolved = git("merge-base", ref, "HEAD")
        if resolved.returncode:
            continue
        base = resolved.stdout.strip()
        changed = git("diff", "--name-only", "--no-renames", "-z", base, "HEAD")
        if changed.returncode:
            raise ValueError("cannot read required-evidence debt changed paths")
        present = git("ls-tree", base, "--", REGISTER)
        if present.returncode:
            raise ValueError("cannot inspect push-base debt register")
        previous, base_specs = None, {}
        if present.stdout:
            content = git("show", base + ":" + prefix + REGISTER)
            if content.returncode:
                raise ValueError("cannot read push-base debt register")
            previous = content.stdout
            for row in map(json.loads, previous.splitlines()):
                spec = git("show", base + ":" + prefix + row["spec"])
                if spec.returncode:
                    raise ValueError("cannot read push-base debt spec: " + row["spec"])
                base_specs[row["spec"]] = spec.stdout
        paths = {p[len(prefix):] for p in changed.stdout.split("\0")
                 if p and p.startswith(prefix)}
        return paths, previous, base_specs
    raise ValueError("cannot resolve trunk range for required-evidence debt; no exemption granted")


def payoff(validator, root, row, base_specs):
    """An absent debt row must be a real payoff of the original pair and requirements."""
    spec, proof = root / row["spec"], root / row["proof"]
    reason = "historical pair requires passing evidence at its original paths: "
    if not spec.is_file() or not proof.is_file():
        return validator.fail(row["proof"], reason + "spec or proof missing")
    old = validator.front_matter(base_specs[row["spec"]])
    current = validator.front_matter(spec.read_text())
    data = json.loads(proof.read_text())
    if not old or not current or not old.get("id") or not (
            old["id"] == current.get("id") == data.get("spec_id")):
        return validator.fail(row["proof"], reason + "spec/proof identity changed")
    if not set(old.get("required_evidence", [])).issubset(current.get("required_evidence", [])):
        return validator.fail(row["proof"], reason + "base required kinds removed")
    return validator.check_required_evidence(spec, proof)


def check(validator, root, rows, changed, previous, base_specs=None):
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
        current_pairs = {(row["spec"], row["proof"]) for row in rows}
        for row in old_rows:
            # Rows still failing are refused by the touch check below. Every removed
            # row must pass at the original paths, even if the register alone changed.
            if (row["spec"], row["proof"]) not in current_pairs:
                errs += payoff(validator, root, row, base_specs or {})
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


def validate(validator, root, matched, policy=None, gate=False):
    rows = compute(validator, root, matched)
    if gate and (policy is None or policy.BASE is None):
        # A debt-free fresh adopter (no shortfall and no register) has no trunk to measure
        # and nothing to ratchet, so it needs no authority base. Anything with debt does.
        if not rows and not (root / REGISTER).exists():
            return 0
        return validator.fail(REGISTER, "gate requires authority BASE; no exemption granted")
    try:
        changed, previous, base_specs = push_context(root, policy)
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
        return check(validator, root, rows, changed, previous, base_specs)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return validator.fail(REGISTER, str(exc))
