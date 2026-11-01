# VELDO-0173 and VELDO-0165: open gap, pinned Claude Code bytes gone from the host

Recorded 2026-10-31, batch 2026-10-29 round 4 (builder G). Nothing was changed in either suite, either
extractor, either record, or either specification on account of this gap.

## What happened

The batch gate on dcf7955b failed five confined-leg rows:

- VELDO-0165 evidence/completeness, evidence/outside-scan
  (scripts/suites/82_veldo_0165_launch_hygiene.py)
- VELDO-0173 evidence/registry, evidence/classification, fixture/extraction
  (scripts/suites/82_veldo_0173_tool_registry.py)

Detail: `[Errno 2] No such file or directory: '/home/dmitry/.local/share/claude/versions/2.1.281'`.
Claude Code updated itself on the gate host and deleted 2.1.281. On 2026-10-31 the host's versions
directory holds 2.1.303, 2.1.312, 2.1.314 and 2.1.316. A filesystem search found no other copy of
2.1.281. The bytes the committed records describe are sha256:56fe3da8...dce1
(proof/VELDO-0173/claude-tools.json).

## What the specifications say

- VELDO-0173 AC1 names the version: "a classification step records in proof/VELDO-0173 every tool of
  the pinned 2.1.281 registry". The registry is "read from its bytes by an extractor this specification
  commits". AC2 requires the registry and classification of a version to be "all read from that
  version's bytes".
- VELDO-0165 AC1 names the versions: "A committed extractor reads every environment variable name each
  pinned binary (Claude Code 2.1.281, Codex 0.154.0) holds in its bytes into proof/VELDO-0165".
- Both put "other versions and host kinds (Release 4)" out of review scope. VELDO-0165 also defers names
  a later version adds to a requalification.

Neither specification says what a host must do once the pinned bytes are gone:

1. No re-pin procedure. Moving to 2.1.316 would replace "2.1.281" in AC text (VELDO-0173 AC1, VELDO-0165
   AC1), which only the owner can change. It would also be a requalification of a new version, which
   both specifications place out of scope (Release 4). It would need a fresh registry, a fresh
   classification of every tool (the lead reviews it before switch-off) and a fresh environment
   extraction.
2. No declared skip. Neither specification says the evidence rows may skip when the pinned bytes are
   absent. Adding a skip would let the rows pass without the evidence the criteria require.

So the cases stay red on this host. Nothing was invented.

## Decision needed (owner)

Pick one and write it into the specifications:

- (a) Restore the pinned bytes. Put the 2.1.281 binary with the recorded digest back at its path, or at
  a path the suites read. Then the criteria stand unchanged and the rows can go green.
- (b) Re-pin. Amend VELDO-0165 AC1 and VELDO-0173 AC1 to a version installed on the host, then
  re-extract, re-classify (lead review) and re-record under the specifications' own procedure.
- (c) Declare a skip. Amend the criteria so the byte-evidence rows skip, by name, when the pinned bytes
  are absent. The committed records would still be checked for internal consistency.

Pinning matters only if the host can be told not to delete a pinned version. Without that, (b) breaks
again at the next auto-update.

## Resolved 2026-11-01: option (a), the pinned bytes restored

The 2.1.281 binary was downloaded from the publisher's release store
(downloads.claude.ai/claude-code-releases/2.1.281/linux-x64/claude). The release manifest's checksum
for linux-x64 and the downloaded file's sha256 are both 56fe3da88458465fb27d7e9299dddb3fead55750fb9c2de795f233b5eea6dce1,
the digest proof/VELDO-0173/claude-tools.json records. It is installed, mode 755, at
/home/dmitry/.local/share/claude/versions/2.1.281; the active Claude Code (the ~/.local/bin/claude
link, 2.1.316) is unchanged. No criterion, record or code changed.

The installer's cleanup may remove this version again. The same two commands restore it:
fetch that URL, check the sha256 above, install it at the same path.
