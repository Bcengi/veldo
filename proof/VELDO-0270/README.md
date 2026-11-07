# VELDO-0270 build status (stopped on a guard block)

## What is built

- AC1(a), commit e28c5ed6: .veldo/validate.py and its canon engine/.veldo/validate.py gain
  `proof-files` and `push-proof` modes and run `check_proof_files` in `all`. Refusals:
  proof_file_over_limit, proof_encoded_archive, proof_reference_dangling,
  proof_summary_incomplete, proof_policy_invalid (key present but not a positive integer).
  The limit is proof.max_file_bytes, default 1,048,576 bytes; protected refs are
  proof.protected_refs, default refs/heads/main and refs/tags/*.
- AC1(b) partial, commit 64242e95: scripts/veldo-guard.sh (synced to engine/scripts and
  packs/claude/scripts) runs `validate.py push-proof` on the ref lines in VELDO_PUSH_REFS
  (remote in VELDO_PUSH_REMOTE), after the emergency lane, so VELDO_EMERGENCY still passes and
  is recorded.

## Why the build stopped

The repository's PreToolUse guard (scripts/veldo-guard.sh) blocked a shell command that rewrote
the seven packs/*/hooks/pre-push files. The command did not push; it matched the guard's
push pattern because the hook text being written contains the push command string. The brief
says to stop and report on any guard block, so the build stopped here. No guard was bypassed.

## Still open

- AC1(b): packs/*/hooks/pre-push must hand git's stdin ref lines and the remote name to the
  guard (VELDO_PUSH_REFS, VELDO_PUSH_REMOTE). Not done. Until then the guard's new check never
  runs from a real hook.
- AC1: policy keys proof.max_file_bytes and proof.protected_refs not yet written into
  .veldo/policy.yaml (the defaults apply).
- AC2: writers (gate transcript capture, mutation writers, proof drivers, corpus audits) not
  changed.
- AC3: the eight files over the limit not yet replaced by summaries; manifests not re-pointed.
  Note: until AC3 lands, `validate.py all` reds proof_file_over_limit on those eight files.
- AC4: the rule paragraph not yet in CLAUDE.md, VELDO.md, engine/VELDO.md, packs.
- Suite, manifest.json and requires.json registration, teeth mutations: not done.
- Falsifiers: none run; no suite was run, so no lock was taken.

## Decision needed from the lead

Whether editing files whose content contains the push command string, through the Edit tool
rather than a shell command, is acceptable under the guard, or whether the guard's matcher
should be narrowed first (a separate ticket).
