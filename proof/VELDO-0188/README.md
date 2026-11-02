# VELDO-0188 proof (branch agent/claude/veldo-0188)

- Suite: scripts/suites/116_veldo_0188_project_lines.py. It was renumbered from 113 in round 3, because 113 is
  used on other branches. Logs from earlier rounds keep the old name.
- Red then green: falsifiers.json, with the full coordinator receipt in falsifiers-receipt.json. It comes from
  check_gate_mutations.py, run under the host gate lock for all nine registered cases (round 3). Suite 116
  runs in the gate's unconfined leg (scripts/gate_unconfined.json, owner approval Telegram 37451 and 37452).
- Rounds: round2/README.md and round3/README.md.
- Open points and deviations: OPEN.md.
- Not run here (owner rule 37191): the full gate.
