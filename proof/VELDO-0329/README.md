# VELDO-0311 hook deadline follow-up

Base: ac6f47fe, branch veldo-space-0329b. This supersedes the manifest's
last assumption about a TERM-ignoring CLI surviving its hook.

Both hook shells catch TERM with `trap : TERM` while waiting for the foreground
CLI. GNU timeout signals their process group; keeping the waiting shell alive
lets `timeout -k 2 10` reach its group KILL after the grace period. A caught
signal resets on exec, so an ordinary CLI still terminates on TERM. This keeps
the existing pipelines, input handling, and success exits; the marked line's
`|| :` still lets git continue after KILL. No new supervisor is needed.

Neither engine hook is protected by this branch's policy. No protected path was
changed. The root and engine reconciler copies are identical; these engine
hooks have no root counterparts.

The new `space329/followup/cli-ignores-term` row uses a stub CLI and child that
both catch TERM and sleep. It exercises both installed hooks and both CLI
invocation arms, checks TERM reached all six processes across three starts,
and checks no process remains running after the hooks return. A bounded
one-second observation wait allows the kernel to finish exits after KILL.
The CLI receives every refs/ line; the owner's hook also receives git's HEAD
line. Real spool submission against a blocked stub authority leaves the
undelivered main-ref event byte-for-byte intact. All fixtures are temporary.

Final checks, all run with `nice -n 10`:

| Check | Result |
| --- | --- |
| 150_veldo_0329_hook_install | 47 passed, 0 failed (21 suite rows) |
| 153_veldo_0323_hook_events | 66 passed, 0 failed |
| 153_veldo_0314_session_hooks | 54 passed, 0 failed |
| .veldo/validate.py all | Exit 0 |
| scripts/check_docs.sh | Pass, exit 0 |
| scripts/check_template_sync.sh | Pass, 324 pairs, exit 0 |

The selected suites exit 2 by design and include 26 shared assertions. No full
gate was run. Only the three explicitly requested suites were selected.

Falsifier: restore both old hook files from ac6f47fe in a temporary copy, with
their original CLI lines and no TERM trap. Exactly the new row goes red because
the CLI and its child survive the ref hook: 20 suite rows pass, 1 fails. The
falsifier cleans its own PIDs. The fixed row passes.

Teeth ran last: `check_teeth_mutations.py --finding 329` passed, 18 registered,
18 executed, 18 rejected, 0 reused, 20 worker invocations, 0 surviving workers,
0 invalid results (82.633 seconds). An earlier run exposed the exit-observation
race in the unchanged control; the bounded observation wait fixed it. No
worktree writes occurred during either teeth run; the final run was followed
only by recording this summary and committing. After every run, no
`space supervise` process from these runs survived.

## Gate fix round, 2026-11-16

Implementation `94952250`, tested with the other fixes at `50c69b7ee35a36f6ea8fa729ea3e913058a24624`. The installer and both
missing-hook reports now live in control_space_install.py and its engine copy; the scaffold
ships that module, and installation.py supplies the child environment. The accepted footprint
widening is dated in the spec History. The 0307 invariant and all acceptance criteria are unchanged.

Selected suites pass: 0329 (47 rows), 0307 (51), 0315 (61), 0259 (46), 0304 (77), scaffold
(898), and upgrade equivalence (60). Counts include dispatcher prerequisites.
All ran with nice -n 10. Personal-setup checking reports zero findings. No full gate was run.

Teeth 329 ran last with the 154, 307 and 315 checks: 18 executed, 18 rejected,
0 reused, zero invalid results and zero surviving workers. The final four findings reject
all 90 mutations. No worktree writes occurred during the teeth runs, and no space supervisor
remained. The 0315 README records the initial invalid test configurations, their reruns, and
the unresolved 0208, 0215 and host-reader rows.
