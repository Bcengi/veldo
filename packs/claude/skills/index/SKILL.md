---
description: Regenerate the specification index and run the weekly index pass.
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

Run scripts/update_index.py, then perform the index pass on: $ARGUMENTS

The pass (15-20 minutes, the one ritual Veldo keeps): close what shipped, kill
or re-own what went stale, adjust priorities, confirm the next ready
specifications. Propose status changes to the human rather than silently
changing intent. If the pass regularly needs more than 20 minutes, say so:
the specifications are too large or the index has drifted.
