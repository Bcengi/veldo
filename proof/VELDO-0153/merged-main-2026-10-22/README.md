# VELDO-0153 on main d49581b4, 2026-10-22

Status: BLOCKED on a host that permits AF_UNIX sockets, exactly as review-corrections.md
recorded; nothing that can run here regressed on the merged tree. This is focused evidence,
not a gate stamp, a review verdict or a landing decision. Direct results and log digests are in
results.json beside this file.

Branch agent/claude/fix-VELDO-0153 is agent/codex/veldo-0153-b2 (32c7ee2c) with main d49581b4
merged in (only WARP-1404 evidence and suite 15 came from main; no conflicts). No production
module, suite or fixture changed in this round.

## What ran here

- `python3 scripts/secret_inventory.py` on the merged tree: 0 outstanding, 281 dispositioned.
  Main's dispositions c416bf44 and f9e9e17d (the suite-107 fixture token line and the
  identity_wire TOKEN literal) still cover the lines where the branch moved them.
- Static checks all exit 0: lint, docs, template sync, validate.py all, check_generated.sh.
- Every one of the 22 finding-153 mutation anchors occurs exactly once on the merged tree.
- `--suite 108_veldo_0153_executor_profile`: 6 rows pass, 32 of 32 assertions pass.
- `--suite 107_veldo_0153_identity_push`: the publication rows and the refusal units run and
  report (publication observations complete, stale rejected; three refusals bound to
  identity_transport_config), then the suite dies at `_v153_fence_rows` when
  scripts/suites/support/identity_wire.py:168 creates the fixture SSH agent's AF_UNIX socket:
  `PermissionError: [Errno 1] Operation not permitted`.
- `--suite 58_veldo_0028_effects`, `--suite 103_veldo_0142_git_identities` and
  `--suite 67_veldo_0056_candidates` die at the same line before their first row. The two
  consumer rows the branch's baseline-comparison.json attributes to this ticket
  (VELDO-0142 lander/worker-commit-mismatch; VELDO-0056 git-failures-refuse and
  every-git-operation-checked) therefore cannot be observed or repaired here.

## Still outstanding

- Host with AF_UNIX: suites 107, 58, 103 and 67 in full, the 26 red consumers and the 12
  incomplete ones in consumer-suites.json, and the fixture work README.md:63-64 names
  ("Their fixtures still need identity-aware transport adapters").
- The live GitHub qualification through proof/VELDO-0153/host_check.py (SSH agent and Secret
  Service credentials).
- Owner: approval of the four consumers that invoke prohibited mutation drivers
  (README.md:56-57); two independent reviews and the recorded approval (risk critical).
- When VELDO-0174 lands too, the second of the two suites numbered 107 resolves a text
  conflict in scripts/suites/manifest.json and requires.json.
