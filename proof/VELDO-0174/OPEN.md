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
- AC4 wording changed on 2026-11-02 (spec History): the conversation receiver is written to the
  installation's state directory and found there by name, no longer beside the repository receivers and
  named in the record's `receiver` as `conversations`. Suites 0189 (kept/owner-data with
  upgrade/from-8bc34e94) and 0171 (rerun/over-0139-host) leave no other place for it. The owner confirms or
  rejects the change in an approved criterion.
- Not covered: a setup re-run whose dispatch step adds adapters to project receivers that held none does not
  add them to the conversation receiver (control_factory_setup_dispatch covers the installation's project
  receivers only). A fresh setup with dispatch gives the conversation receiver its adapters at install.

## 2026-11-03: suite 106 row loop/configured strengthened

Gate 0174b at c6790fd6: every stage green except mutation, where v185-work-not-installed survived on its
named row loop/configured (the conversations receiver alone starts the loop, so the loop reports configured
with no work installed). The row now also checks the enrolled repository's line is held by the loop.
Suite 106: 20 of 20 passed; with work=None applied by hand: loop/configured false (lines []).
