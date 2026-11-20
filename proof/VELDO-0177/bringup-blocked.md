# VELDO-0177 not brought onto the line, 2026-11-20

Source branch: `agent/claude/veldo-0177` at f14eea14 (2026-11-18): 20 commits of its own
(9d1cb6f0..8d04ad70) and a saved work-in-progress commit, on top of ten commits of VELDO-0231.
Tried on the line at b7c7021c (space-0329b at 0b767d26 with VELDO-0111, VELDO-0117 and VELDO-0124
brought over). Nothing of VELDO-0177 is committed; this file is the only change.

## The block: VELDO-0231 is underneath it and is not on the line

Every conversation branch (VELDO-0175 to 0181, 0183, 0184, 0187) starts with the same ten commits
of VELDO-0231 ("a running agent can flag something to the lead without stopping"), then
VELDO-0177. VELDO-0231 is not on the line: no specification, no suite, no code. It is not one of
the seventeen tickets of this bring-up and VELDO-0177's `depends_on` does not name it, but the
code needs it:

- `control_factory_setup_dispatch.py` (the assistant roles setup saves) reads
  `control_agent_config.WAIT_QUESTION_TOOLS`, which VELDO-0231 adds.
- Suite 128_veldo_0177_conversation_workspace drives its turns through
  `scripts/suites/support/v231_fake_engines.py`, VELDO-0231's fake engines.

VELDO-0177's own diff (1c0f9d67..f14eea14) was ported onto the line without VELDO-0231, taking
only its own halves of the three conflicts (`control_conversation.py` constants and helpers,
`control_launch.py` receiver fields, `scripts/gate_unconfined.json`). All 340 mutants registered
on the five modules it touches still anchor once. The suites, each alone:

| Suite | Result without VELDO-0231 |
| --- | --- |
| 128_veldo_0177_conversation_workspace | does not load: `support/v231_fake_engines.py` is missing |
| 129_veldo_0177_assistant_setup | 0 of 4 rows: no attribute `WAIT_QUESTION_TOOLS` |
| 106_veldo_0185_dispatch_setup | red on every setup row, same attribute |
| 123_veldo_0174_conversations | 37 rows passed, AC2/restart-turns failed |

So this is not a conflict with the line's design. It is a missing ticket. VELDO-0231 is
`risk: high`, `human_approval: required`, built on `agent/claude/veldo-0231` at 3c8603b0 (13
commits: the ten above, reviewed SOUND on 2026-11-04, and fix round 1). Bringing an eighteenth
ticket was not part of this bring-up, so it was not done.

## What bringing VELDO-0231 takes

A trial port of `agent/claude/veldo-0231` (d186ec93..3c8603b0) onto the line gives thirteen
conflicts. Four are code (`control_launch.py` beside VELDO-0350's fields, `control_service.py`
beside VELDO-0260's watched trees, `qualify.py`, `proof/VELDO-0127/delivery_fixture.py`). The
rest are generated files: `runtime/codex-qualification.json` (both copies) and the four
`proof/VELDO-0127/resources-*.json` fixtures. Those bind the digests of `control_agent_config.py`,
`control_agent_config_handoff.py`, `control_engine_claude.py`, `control_engine_codex.py` and
`control_launch.py` and the recorded engines' answers, so they are not merged by hand: they are
written again by `python3 .veldo/qualify.py --codex <binary> --claude <binary>` on the engines
record's binaries (Codex 0.166.0, Claude Code 2.1.317), as fe9eb598 did after the launch-wait
change. VELDO-0231 adds a flag probe to that command, which starts both engines against a
loopback capture.

The same regeneration is due after each conversation ticket that changes one of those five
modules (VELDO-0177, VELDO-0176 and VELDO-0184 each do).

## Also to decide at landing

`scripts/gate_unconfined.json` is a protected path. VELDO-0177 adds suites 128 and 129 to it
(1ea19243, "protected, owner approval at landing"). On the line the numbers 128 and 129 are also
used by VELDO-0254's suites; the names do not collide.

## Blocked with it

VELDO-0176, 0175, 0178, 0179, 0180, 0181, 0183, 0184 and 0187 each depend on VELDO-0177 (directly,
or through VELDO-0178, VELDO-0175 and VELDO-0176) and were built on top of it. Each has a short
`bringup-blocked.md` of its own pointing here. The order once VELDO-0231 is on the line:
0177, 0176, 0175, 0178, then 0179 and 0180, 0181, 0183, 0184, 0187.
