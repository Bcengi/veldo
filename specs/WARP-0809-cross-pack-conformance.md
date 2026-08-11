---
schema: veldo.spec/v1
id: WARP-0809
title: Cross-pack conformance - a table-driven harness proving every pack enforces the VELDO invariant by construction
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0008
work: W9
plan_revision: 1
depends_on: [WARP-0802, WARP-0803, WARP-0804, WARP-0805, WARP-0806, WARP-0807, WARP-0808]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A table-driven cross-pack conformance harness exists (.veldo/pack_conformance.py, build
      machinery, driven from .veldo/packs.json), wired into the gate via the selftest. Run over the
      repository it reports every declared pack conformant - a single findings list that is EMPTY
      when all packs hold and names the pack and failure otherwise.
  - id: AC2
    text: For EACH declared pack the harness drives the pack against its OWN assembled engine through
      a constructed VELDO state and proves the push gate is real, not honor-system (NG2) - the pack's
      copied guard (through its committed git pre-push hook where it ships one, else the guard
      directly) BLOCKS a push at an unproven HEAD (exit non-zero) and ALLOWS one at a proven HEAD
      (green last_verify + a proof manifest + a passing commit-bound verdict, evidence-inheritance
      honored), and policy_check.py run standalone exactly as CI runs it agrees (blocks the unproven
      state, passes the proven state). Asserting BOTH directions per pack is intrinsic teeth: a
      state-blind gate cannot satisfy block-unproven AND allow-proven.
  - id: AC3
    text: The harness closes the WARP-0808 review note at the git INDEX - the committed mode of every
      pack's hooks/pre-push and copied scripts/veldo-guard.sh is asserted executable (100755) via
      git ls-files -s (stronger than a working-tree os.access check, which can diverge from the
      index), and a real git-invoked push to a local bare remote proves the exec bit is load-bearing
      end to end: a committed non-executable hook fails OPEN (git silently skips it, an unproven push
      lands), an executable one BLOCKS the unproven push.
  - id: AC4
    text: The engine drift-check holds across all seven packs (byte-identical content AND mode),
      asserted by the harness for every declared pack, so portability and no-drift are gate-enforced
      by construction, not by inspection - the join point that converts "ported" into a property.
  - id: AC5
    text: A selftest asserts the harness passes (findings empty) and is non-tautological - the
      per-pack both-directions assertion (block unproven, allow proven) is teeth by construction, the
      real-git-push exec-bit case reproduces the fail-open on a non-executable hook and blocks with
      the executable one, and the committed-index-mode assertion covers every pack's hook and guard.
required_evidence: [unit]
rollback: git revert; additive - a new .veldo/pack_conformance.py build-machinery module (not shipped
  engine, not copied into packs), a selftest block, and this spec; no protected path; pure stdlib,
  the per-pack gate driven locally (no network) plus one local-bare-remote push for the exec-bit
  teeth.
---

## Intent

W9 is the join point of PLAN-0008: it cannot run until all seven packs exist, and it converts "the
packs were ported" into a property the gate ENFORCES for every pack, by construction. The prior
per-pack specs (W2-W8) each asserted their own pack's structure and wiring; W9 adds a single
table-driven harness that drives EACH declared pack through a constructed VELDO loop against its own
assembled engine and proves the push gate genuinely blocks an unproven push and allows a proven one,
that policy_check agrees, that the committed hook and guard are executable in the git index, and that
no pack's engine has drifted. Portability and no-fail-open stop being things a human inspects and
become things the gate proves.

## Context

W9 of PLAN-0008, depends on every pack (W2-W8). The harness is build machinery in the repo-root
.veldo/ (like pack.py and tracker_conformance.py), not shipped engine, so it is not copied into packs
and does not itself drift. It reads the pack manifest (.veldo/packs.json), so a new pack is covered the
moment it is declared. The gate is driven locally without a network: each pack is extracted with git
archive (mode-preserving), committed into a throwaway repo, and its committed pre-push hook (or the
guard directly, for the option-B Claude pack that ships no committed hook of its own) is invoked
against a constructed unproven vs proven state; one real git-push-to-a-local-bare-remote case proves
the exec bit is load-bearing end to end.

## Notes

This spec also closes the non-blocking robustness note the WARP-0808 review raised: the per-pack
selftest blocks asserted working-tree executability (os.access X_OK), which can diverge from the git
index, and the mode-aware drift-check covers only engine files (a wrapper hooks/pre-push is a per-pack
authored file, not engine). W9 asserts the COMMITTED index mode (git ls-files -s) of every pack's
hook and guard, so a future commit landing a wrapper hook at 644 while the local tree is 755 is caught
at the gate. The proven-state fixture is a single-commit repo (so policy_check's changed-files
fallback sees no protected paths) carrying a green last_verify, a proof manifest, and a passing
commit-bound verdict whose proof_digest matches the manifest, exactly the shape policy_check requires.
The guard's CLAUDE_PROJECT_DIR is pinned to the fixture so an inherited session value can never
redirect the guard at the wrong repository. Driving both the block and the allow direction for every
pack is the teeth: a gate that ignored repository state could not satisfy both at once.
