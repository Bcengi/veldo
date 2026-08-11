---
schema: veldo.spec/v1
id: WARP-1102
title: Gate enforcement of the mechanizable shape rules - the architecture contract's mechanizable rules fail the build, not the retrospective (W2 of PLAN-0011)
status: shipped
risk: high - touches the protected gate path scripts/verify.sh (policy.yaml floor high), so it needs recorded founder approval regardless of the footprint tier; the footprint spans the enforcement and contracts areas, joined by the allow-listed enforcement -> contracts edge, so it is cohesive breadth (footprint tier standard) not a boundary crossing
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0011
work: W2
plan_revision: 2
depends_on: [WARP-1101]
protected_paths: [scripts/verify.sh, engine/scripts/verify.sh]
placement: [enforcement, contracts]
footprint:
  - specs/WARP-1102-gate-shape-enforcement.md
  - scripts/verify.sh
  - scripts/selftest.py
  - .veldo/shape_gate.py
  - .veldo/capabilities.yaml
  - .veldo/init_scaffold.py
  - engine/scripts/verify.sh
  - engine/.veldo/shape_gate.py
  - engine/.veldo/capabilities.yaml
  - packs/*/scripts/verify.sh
  - packs/*/.veldo/shape_gate.py
  - packs/*/.veldo/capabilities.yaml
acceptance_criteria:
  - id: AC1
    text: >
      The mechanizable shape rules are enforced at the gate and fail closed with the rule
      NAMED. .veldo/shape_gate.py reads the architecture contract (veldo.arch/v1) and, for every
      rule the contract marks enforcement: mechanizable, applies an enforcement that refuses a
      violation and fails scripts/verify.sh with the rule named (outcome O2). What is gate-blocking
      today, driven by THIS repository's contract labels, is: the module size budget (the
      file_lines budget module_lines, refused over the change set with the budget id named); and
      the engine invariants engine_byte_identical, derived_never_authoritative, and
      adoption_safe_fail_closed, each mapped to a wired enforcement (check_pack_drift.py plus
      check_template_sync.sh; check_generated.sh; and this gate's own stand-down respectively) and
      refused by name if a named enforcing catalog check is absent (the enforcement may never
      silently vanish). The check reuses validate.parse_yamlish and arch.area_for_path plus the
      boundary-graph helpers (no second parser, glob compiler, or boundary implementation). A
      selftest asserts each mechanizable rule enforces and names itself over fixtures, and a
      standalone run of python3 .veldo/shape_gate.py over this repository returns 0 with the
      mechanizable rules enforced.
  - id: AC2
    text: >
      Adoption safe (C2): a repository with NO architecture contract stands the whole shape gate
      down. shape_gate.run over a temporary tree with no .veldo/architecture.yaml returns standdown
      True and no problems, and python3 .veldo/shape_gate.py in such a tree prints one standdown line
      and returns 0, so adding this check to verify.sh changes no existing gate and a contract-free
      repository is byte-identically unaffected. Proven over a temporary tree in the selftest.
  - id: AC3
    text: >
      Green safe and CHANGE SCOPED, never a corpus re-sweep (the W3 posture restated). The size
      budget binds only the files THIS change touches (the diff against the trunk plus the working
      tree, computed via git; runtime and derived artifacts .veldo/last_verify, .veldo/events.jsonl,
      specs/index.md, and proof/ are excluded), so the already-shipped corpus is grandfathered
      exactly as W3's placement gate never re-sweeps shipped specs. This is the only green-safe
      reading here: this repository's own .veldo/validate.py (1207 lines) already exceeds the
      1000-line file_lines budget as a pre-contract module, so a whole-tree corpus sweep at the
      budget max would turn the current green gate RED; the size rule must not. A selftest asserts
      a changed governed file over the budget refuses (RED) while the same file unchanged (not in
      the change set) is untouched, and ./scripts/verify.sh is GREEN over the whole current repo
      after this change (the enforcement did not break our own build).
  - id: AC4
    text: >
      The stdlib reference implementations for the boundary, function-length, duplication, and
      complexity checks ship as the D6 pluggable per-language slot in .veldo/shape_gate.py, honestly
      labeled: they are enforced (gate-blocking) only when the contract marks their rule
      enforcement: mechanizable AND the code is proven to pass, and while the contract marks them
      enforcement: review (as it does today for dependency boundaries, function_lines, duplication,
      and complexity) they are surfaced as NON-BLOCKING notes over the changed governed sources,
      never a gate refusal (NG5: the gate never carries a vacuous check; a rule that cannot be
      checked mechanically stays honestly in the review lane). Nothing in this item flips a rule
      from review to mechanizable; the contract's enforcement label is the sole authority. A selftest
      proves each reference analyzer detects a seeded violation (non-vacuous) AND that a review-labeled
      rule produces a note that does NOT fail the gate, while the same rule relabeled mechanizable
      DOES fail it.
  - id: AC5
    text: >
      Footprint versus diff (the O3 half W3 deferred to this item) is enforced green safe. When the
      change set names EXACTLY ONE spec that declares a footprint, every changed source path must be
      covered by that spec's declared footprint globs or the gate refuses by name (a change may not
      silently touch a path its spec never declared), reusing the one glob compiler arch._glob_re.
      It stands down when the change set names zero footprinted specs (the clean committed tree) or
      more than one (a multi-spec landing is out of this item's scope, stated honestly), and it never
      re-sweeps the shipped corpus (a shipped spec's footprint is re-examined only if that spec file
      is itself in the change set). This spec (WARP-1102) is the first dogfood instance: it declares a
      footprint covering every path it touches, so the live gate's footprint-versus-diff passes over
      this change. A selftest drives footprint_findings over a fabricated one-footprinted-spec change
      set (a path outside the footprint refuses; within-footprint passes) and over a zero and a
      two-footprinted-spec change set (stands down).
  - id: AC6
    text: >
      RJ1 conformance: a seeded violation of each mechanizable rule class present in the contract
      fails the gate with the rule named, and the clean tree stays green. The selftest seeds, in
      isolation so exactly one rule bites, and observes RED then reverts: a changed governed file
      over the file_lines budget (budget class, names module_lines); a mechanizable prose rule whose
      enforcing catalog check is absent (engine-invariant class, names the rule and the missing
      check); and it confirms the clean current tree yields no shape-gate problems (green). The
      byte-divergent-pack tooth for engine_byte_identical and the stale-index tooth for
      derived_never_authoritative are exercised by their dedicated catalog checks (check_pack_drift.py,
      check_generated.sh), which the shape gate confirms are wired; the selftest also proves the shape
      gate refuses when those enforcing checks are removed.
  - id: AC7
    text: >
      Fail closed and anti-vacuity (C1, C2, NG5): the moment a contract exists the mechanizable rules
      fail closed. A contract that marks a prose rule mechanizable with an id the gate has no wired
      enforcement for is REFUSED by name (you cannot mark a rule mechanizable and enforce nothing), and
      a mechanizable budget of a kind with no reference implementation is refused. shape_gate.main
      fails closed on any unexpected error (never a silent pass). Each refusal class is proven by a
      selftest over a fabricated contract, and the positive control (this repository's real contract,
      whose every mechanizable rule is wired) passes.
  - id: AC8
    text: >
      The change ships byte-identical across all 8 engine copies and the protected-file diff is thin.
      .veldo/shape_gate.py is new engine synced byte-identical to engine and the 6 packs, and
      .veldo/capabilities.yaml gains one honest entry (shape_gate_enforcement, mechanical) synced across
      all 8 copies (pack drift and the byte-identity selftest pass). scripts/verify.sh and its
      engine twin (both protected paths, policy.yaml floor high) gain ONLY a thin call into
      the non-protected .veldo/shape_gate.py (the logic lives outside the protected file); veldo-guard.sh,
      .veldo/policy.yaml, and .veldo/policy_check.py are NOT touched. This spec declares its own placement
      (enforcement and contracts) and footprint and computes to footprint tier standard (enforcement and
      contracts are joined by the allow-listed enforcement -> contracts edge, cohesive breadth under the
      WARP-1011 refined rule, not a boundary crossing); it is nonetheless a PROTECTED-PATH change (it edits
      verify.sh), which is why it carries human_approval: required and the founder's recorded approval,
      independent of the tier. The full gate is GREEN (selftest, contracts, generated, docs, secret scan,
      template sync, pack drift, runner catalog, and the new shape gate) and RULE #1 is clean.
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds one module (.veldo/shape_gate.py: the contract-driven mechanizable-rule
  enforcement, the change-set computation, the file_lines budget enforcement, the prose-rule enforcement
  registry, the footprint-versus-diff check, and the stdlib reference analyzers), a thin call to it from
  scripts/verify.sh and its engine twin, one capabilities.yaml entry, and a selftest block, all
  re-synced byte-identical across engine and the 6 packs. The shape gate stands down entirely when
  no architecture contract exists (adoption safe), so a repository without a contract is unaffected either
  way; reverting returns the gate to its prior behavior with no migration and nothing to unwind. The already
  shipped corpus was never re-swept (change scoped), so nothing about the historical tree changes on revert.
---

## Intent

This is W2 of PLAN-0011, the gate-time move of the decay half of the architecture
organ. W1 made the intended shape a versioned, human-approved contract
(.veldo/architecture.yaml, veldo.arch/v1) and validated it STRUCTURALLY; W3 made every
spec declare its placement and footprint before anything is built. This item makes
everything MECHANIZABLE about the declared shape a check that FAILS: a change that
violates a size budget, or an engine invariant the contract marks mechanizable,
fails scripts/verify.sh with the rule named, before any reviewer sees it (outcome
O2). Architecture stops being taste at merge time and becomes a check that refuses.

The honest reading of "mechanizable shape rules" is load bearing. ONLY rules the
contract marks enforcement: mechanizable become gate-blocking. Rules marked
enforcement: review (today: the dependency and import boundaries, the function-length,
duplication, and complexity budgets, and most prose patterns and invariants) stay
reviewer guidance, surfaced as non-blocking notes, never a gate refusal (NG5: the gate
never carries a vacuous check that cannot refuse, and a rule that cannot be checked
mechanically stays honestly in the review lane). This keeps the gate green by enforcing
exactly what the code already satisfies, not by making the new check toothless.

Two constraints shape the design. First, this repository carries its OWN contract, so
the moment enforcement is wired the repository's own code is subject to it: the gate
must enforce only what the current code passes and stay green. The size budget is
therefore CHANGE SCOPED (it binds the files this change touches, never a corpus
re-sweep), exactly as W3's placement gate is enforced at the transition and the claim
and never sweeps the shipped corpus; this grandfathers the pre-contract .veldo/validate.py
(1207 lines, over the 1000-line budget) while stopping any NEW over-budget module.
Second, the shape check touches the protected gate path scripts/verify.sh, so the logic
lives in a non-protected module (.veldo/shape_gate.py) that verify.sh CALLS with a thin
two-line addition, minimizing the protected-file diff.

## Context

- Depends on WARP-1101 (shipped): the architecture contract at .veldo/architecture.yaml
  (veldo.arch/v1) and .veldo/arch.py, whose area_for_path, area_ids, _glob_re, _allowed_edges,
  and _areas_connected this item reuses (the one place a path resolves to an area and a
  modeled boundary is defined), loaded through validate.load_repo_contract (the one contract
  loader).
- W3 (WARP-1103, shipped) explicitly deferred gate-time footprint-versus-diff enforcement to
  this item; this item enforces it, scoped green safe (exactly one footprinted spec in the
  change set), and this spec dogfoods it.
- Resolved decision D6: stdlib-proportionate reference implementations with a pluggable
  per-language slot; external analyzers stay optional per-repo extensions. The reference
  boundary, function-length, duplication, and complexity analyzers ship in shape_gate.py behind
  the contract's review label.
- The two postures the plan binds everywhere: adoption safe (no contract stands the whole gate
  down) and fail closed (the moment a contract exists a mechanizable rule refuses, and a
  mechanizable rule the gate cannot enforce refuses by name).

## Out of scope

- No corpus re-sweep of the shipped tree. The size budget binds the change, not the historical
  corpus; bringing the pre-contract .veldo/validate.py under the budget is a restoration unit for
  the W8/W9 entropy loop, not this gate's job. A whole-tree size sweep would turn the current
  green gate red and is deliberately not done.
- No flip of any rule from review to mechanizable. The contract's enforcement label is the sole
  authority; this item enforces the labels as written and ships the reference analyzers for the
  review-lane rules behind that label.
- No new-module detection beyond the footprint declaration. Deciding a change creates a genuinely
  new module still needs the diff plus judgment; the footprint-versus-diff check enforces the
  DECLARED footprint over the diff, which is the well-defined gate-time signal.
- No entropy metrics or restoration. Deriving per-area cost-to-change and generating restoration
  specs is WARP-1108/WARP-1109 (W8/W9).
- No change to veldo-guard.sh, .veldo/policy.yaml, or .veldo/policy_check.py. The only protected
  paths touched are scripts/verify.sh and its engine twin, each gaining a thin call.

## Notes

- Keep the protected-file diff thin: verify.sh gains a single built-in block that calls
  python3 .veldo/shape_gate.py and sets FAIL on a non-zero exit; all logic lives in the
  non-protected module.
- Change scoping via git: the change set is the working tree (unstaged and staged) plus untracked
  files plus the commits ahead of the trunk (merge-base..HEAD), minus the gate's own runtime and
  derived artifacts. When git is unavailable or nothing changed, the size and footprint rules have
  nothing to bind (green), never a corpus sweep.
- Put teeth on each behavior (C1): a changed governed file over the budget turns the gate RED and
  reverts; a mechanizable prose rule with no wired enforcement or a deleted enforcing check refuses;
  the reference analyzers each detect a seeded violation; footprint-versus-diff refuses a path
  outside the single footprinted spec's footprint; and the clean current tree passes green.
- RULE #1 clean (ASCII hyphen only, no em or en dash, no prose double-hyphen).
