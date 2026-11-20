# VELDO-0176 not brought onto the line, 2026-11-20

Source branch: `agent/claude/veldo-0176` at 4a83cc5e (2026-11-04),
7 commits naming the ticket among 34 not on the line. Last commit: "VELDO-0176: independent review, SOUND".

Blocked behind VELDO-0177, which is blocked because VELDO-0231 is not on the line and is not one
of the tickets of this bring-up: see proof/VELDO-0177/bringup-blocked.md. This ticket needs
VELDO-0177 (depends_on), and it changes control_launch.py, control_engine_claude.py and control_engine_codex.py, so the qualification files are written again after it. Its branch is built on the same ten VELDO-0231 commits and on VELDO-0177, so its
diff does not stand on the line without them.

No port was tried and nothing of the ticket is committed. This file is the only change.
