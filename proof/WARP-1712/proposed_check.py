EVIDENCE_KIND_ALIASES = {
    # Equivalent kind spellings only. A generic test is legacy unit evidence, never integration.
    "unit": {"unit", "test"},
    "integration": {"integration"},
    "journeys": {"journeys", "journey", "e2e"},
    "ui_states": {"ui_states", "state_capture"},
    "figma_composite": {"figma_composite", "composite", "visual"},
    "interaction_recording": {"interaction_recording", "recording", "video"},
    "baseline": {"baseline", "visual_baselines"},
    "device_matrix": {"device_matrix", "matrix"},
    "design_review": {"design_review"},
    "operational": {"operational"},
    "staging_run": {"staging_run", "staging"},
}


def evidence_passed(entry):
    """Require an explicit outcome on this entry, never inherit a criterion's status.

    Proof writers use status=passed or the example's result=pass. All supplied
    outcome fields must agree; prose, missing results and near misses fail closed.
    """
    outcomes = [entry[key] in allowed for key, allowed in (
        ("status", ("passed",)), ("result", ("pass", "passed"))) if key in entry]
    return bool(outcomes) and all(outcomes)


def evidence_kinds_in_proof(data):
    kinds = set()
    for c in data.get("criteria", []):
        for e in c.get("evidence", []):
            if e.get("type") and evidence_passed(e):
                kinds.add(e["type"])
    for ch in data.get("checks", []):
        if ch.get("name") and evidence_passed(ch):
            kinds.add(ch["name"])
    return kinds


CANONICAL_KINDS = set(EVIDENCE_KIND_ALIASES.keys())


def check_required_evidence(spec_path, proof_path):
    """Require passing evidence of each declared kind (or a passing named check).
    design_review requires a passing design-verdict file next to the manifest.
    """
    errs = 0
    fm = front_matter(Path(spec_path).read_text())
    declared = []
    if fm and "required_evidence" in fm:
        declared = fm["required_evidence"]
    if not declared:
        return 0
    try:
        data = json.loads(Path(proof_path).read_text())
    except Exception:
        return fail(proof_path, "unreadable proof for required-evidence check")
    present = evidence_kinds_in_proof(data)
    for kind in declared:
        if kind not in CANONICAL_KINDS:
            errs += fail(spec_path, f"unknown evidence kind '{kind}' (canonical vocabulary: {sorted(CANONICAL_KINDS)})")
            continue
        accepted = EVIDENCE_KIND_ALIASES[kind]
        if kind == "design_review":
            # THROUGH THE ONE ENUMERATION (WARP-0727 round 2), never a private glob. This was a
            # SECOND spelling of a set the corpus owner already declares DESIGN_VERDICT_PATTERN
            # for; it agreed with the owner on this platform, which is what makes it a law
            # violation rather than a live divergence. The owner is asked about the proof root
            # and the answer is narrowed to the manifest's own spec directory, so the membership
            # rule that decides the corpus decides this too.
            _spec_dir = Path(proof_path).parent
            reviews = [p for p in _CORPUS.corpus_in_dir(_spec_dir.parent,
                                                       _CORPUS.DESIGN_VERDICT_PATTERN)
                       if p.parent == _spec_dir]
            passed = False
            for review in reviews:
                try:
                    verdict = json.loads(review.read_text())
                except (OSError, ValueError):
                    continue
                if isinstance(verdict, dict) and verdict.get("verdict") in ("pass", "pass_with_notes"):
                    passed = True
            if not passed:
                errs += fail(proof_path, "required design_review: no passing design-verdict*.json beside the manifest")
            continue
        if not (accepted & present):
            errs += fail(proof_path, f"required evidence kind '{kind}' absent from passing proof entries (matching evidence type or check name needs a passing result)")
    return errs

