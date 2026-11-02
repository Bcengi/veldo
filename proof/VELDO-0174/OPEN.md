# VELDO-0174: open items for the owner

Written 2026-11-02 after main 646b2d68 was merged into agent/claude/fix-VELDO-0174.

## Protected paths

None. `git diff --name-only 646b2d68 HEAD` names no path under `.veldo/policy.yaml`
`protected_paths`, and `python3 .veldo/policy_check.py` exits 0. No approval is asked for and none
was authored.

## Items for the owner or the lead

- The suite is now 123_veldo_0174_conversations (main's 107 is VELDO-0153's). It is not in
  scripts/gate_unconfined.json, which is protected. Its two restart rows start the production
  service and bind its AF_UNIX authority socket. They pass on this host outside any confinement;
  whether the gate's confined leg lets them bind is decided only by the gate run. If they fail
  there, listing the suite is an owner decision (a protected change), not an agent step.
- Suite 86 `live/claude` and `live/codex` fail: missing or stale live capture.
  proof/VELDO-0127/claude-live.json (main's version, retaken in batch 2026-11-01) and
  codex-live.json pin sha256 digests of control_launch.py (main 4498f28c...) and
  control_agent_config_handoff.py (main b73d425b...); this ticket changes both (now 69eff0e9...
  and 9cb6c5fb...). Clearing them needs fresh Claude and Codex live captures on owner accounts
  (proof/VELDO-0127/live.py), taken with owner approval. Not taken here, and no assertion was
  changed to hide them.
