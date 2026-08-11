---
description: Initialize Veldo in this repository - lay down the specs directory, policy, canonical gate, templates, and instructions from the plugin's templates.
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

Initialize Veldo in the current repository. $ARGUMENTS

Steps, in order:

1. Run the scaffolder, which resolves its own template source and copies into
   the repository root, WITHOUT overwriting anything that exists:
   VELDO.md, specs/ (TEMPLATE.md, TEMPLATE-standing.md, index.md), proof/,
   .veldo/ (policy.yaml, validate.py, examples/), scripts/ (verify.sh,
   update_index.py, veldo-guard.sh). chmod +x the scripts.
2. CLAUDE.md: if the repository has none, copy the template. If one exists,
   PREPEND the template's five Veldo rules block behind the marker
   `<!-- Veldo: added by veldo init -->`; if the marker is already present,
   skip this step entirely. Never delete existing content.
3. Hooks: the plugin already enforces the guard while the plugin is enabled.
   Also offer the repo-local wiring (.claude/settings.json) so the
   guard holds for people without the plugin; merge it into the repository's
   .claude/settings.json if the human agrees.
4. Configure with the human (interview, do not guess):
   - scripts/verify.sh slots: this repository's real format/lint/type/test/
     build commands. Run the gate once; it must produce a clear result.
   - .veldo/policy.yaml protected_paths: the paths in THIS repository where
     being wrong is unrecoverable.
5. Run scripts/update_index.py, then python3 .veldo/validate.py all - both
   must pass.
6. Show the human a summary of every file created, and finish with the next
   step: write the first specification with /veldo:spec (or draft it
   together now).

Everything lands as ordinary files in the working tree so the human reviews
and commits the initialization like any other change. Do not commit or push
yourself unless asked.
