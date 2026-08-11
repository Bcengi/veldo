---
description: Run the Veldo canonical gate and interpret failures.
allowed-tools: Read, Grep, Glob, Bash
---

Run ./scripts/verify.sh for: $ARGUMENTS

Report the result plainly. If red: identify each failing check, fix the
defects (never the checks), and rerun until green. Never weaken a test,
skip a check, or edit acceptance criteria to pass. The gate stamps
.veldo/last_verify and appends the gate event itself.
