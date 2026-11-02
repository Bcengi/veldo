# VELDO-0174: review of the merge round of 2026-11-02

Reviewer: fresh context, read-only. Branch agent/claude/fix-VELDO-0174 at c06f165a, main 646b2d68.
Judged against the specification's AC1 to AC4 and the five checks the lead set. The gate
(scripts/verify.sh) was not run. Suites ran one at a time under the host gate lock.

## Verdict: NOT SOUND

One finding. The merge keeps main's VELDO-0188 code, but on the merged tree main's own VELDO-0188
suite goes red, and the cause is 0174's new conversation receiver configuration.

## Finding

1. HIGH. Suite 116_veldo_0188_project_lines fails 4 of 53 on the branch (lines/at-start,
   lines/new-project, lines/adopted-project, lines/restart), in 23.63 s and again in 24.22 s. Main
   646b2d68, exported with git archive and run the same way, passes 53 of 53 in 24.32 s.
   Cause: the served scenario's protocol fake at proof/VELDO-0188/round2/served_scenario.py:100-101
   reads every `receiver-*.json` in the installation's config directory and indexes `r['repository']`.
   0174's installer (engine/.veldo/control_service.py:1129) now also writes `receiver-conversations.json`,
   which by AC4 has no repository. The fake raises KeyError. The dispatch is accepted and exits, but
   `builds/FACTORY-0001.json` is never written, so the scenario times out ("served observation timed
   out"). Confirmed on an exported copy of HEAD with only that lookup changed to `r.get('repository')`:
   53 passed, 0 failed in 24.48 s. Production behavior is as AC4 specifies. This is a test fixture of
   another ticket that assumed every receiver file names a repository. proof/VELDO-0188/ is outside
   0174's footprint, so the fix (or widening the footprint for it) is the lead's decision.
   The round's proof missed this because its suite set (merged-main-2026-11-02/README.md:72) left out 116.
   The gate will show it red.

## The five checks

1. Conflict resolution: holds. engine/.veldo/control_service.py and .veldo/control_service.py are
   byte-identical (cmp). Against main, the diff removes no main line other than ten lines that each
   come back extended: the receiver dict gains receiver_kind, the configs map is filtered to project
   receivers, loop_status counts conversations as configured, work is optional, the counts gain
   conversation_offered, provision falls back to the conversation line, the status gains conversation
   fields, and open_loop accepts no work. main's work_roles, line_counts, refused_lines,
   `follow_store(0)` and the journal-woken `follow_store` are intact. 0174's ConversationLine is built
   before `follow_store(0)`, and in run() the conversation turns go after follow_store and before the
   project lines, so AC3's turn-first order holds. manifest.json only adds 0174's entry; requires.json
   adds three lines.
2. f50f7848: holds. It changes only scripts/suites/107_veldo_0174_conversations.py (+3, pops the
   stand-in's served repository) and scripts/suites/support/v174_journey.py (watermark on the stand-in,
   a served repository, a project team, and roles from line_roles), plus two logs. No production
   module and no check or assertion is changed or removed.
3. Nine re-anchored cases (d5f72fb6): hold. Each new anchor is lengthened only to pick the original
   site over the copy 0174 introduced, and each defect is unchanged:
   - installer-receiver-without-host-trust and authority-receiver-profile-omitted: project receiver,
     not the conversation receiver.
   - dispatch-spawn-before-contract: the unit prepare, not prepare_conversation.
   - dispatch-authority-unchecked: the transition's _authorize, now with subject kind.
   - retire-no-sweep-on-prepare: Runner.prepare, not prepare_conversation.
   - setup186-receiver-without-state-root: project receiver.
   - v204-account-sum-first-project: still truncates the project sum.
   - v204-loop-lock-dropped: open_loop.
   - v204-second-policy-writer: Line.activate, followed by `_rows`, not ConversationLine.activate.
   Run by hand with handmut.py, source restored, `git status` clean afterwards:
   - installer-receiver-without-host-trust on suite 66: RED on authority/receiver-configured-with-host-profile, 2 rows failed.
   - v204-account-sum-first-project on suite 96: RED on derive/values and source/project, 5 rows failed.
4. Suites, each alone:
   - 123_veldo_0174_conversations: 64 passed, 0 failed, 9.69 s.
   - 86_veldo_0127_agent_configuration: 53 passed, 0 failed, 38.05 s (live/claude and live/codex pass on the retaken captures).
   - 116_veldo_0188_project_lines: 49 passed, 4 failed, 23.63 s (finding 1).
5. Protected paths and secrets: holds. `python3 .veldo/policy_check.py` exits 0. .veldo/policy.yaml
   and scripts/gate_unconfined.json are unchanged against main. The captures in c06f165a
   (proof/VELDO-0127/claude-live.json, codex-live.json) pin the current control_launch.py (69eff0e9...)
   and control_agent_config_handoff.py (9cb6c5fb...). A scan for tokens, keys, e-mail addresses and
   home paths found only message ids, tool names and sha256 digests.

## Side observations

- proof/VELDO-0174/OPEN.md:18-24 and merged-main-2026-11-02/README.md:98 still say suite 86 live/claude and live/codex fail; c06f165a cleared that.
