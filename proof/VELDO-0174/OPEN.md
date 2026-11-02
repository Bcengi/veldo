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
- Suite 86 live captures: retaken by the lead (c06f165a); suite 86 passes 53 of 53.
