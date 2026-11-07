---
schema: veldo.spec/v1
id: VELDO-0270
title: Proof is small summaries, never raw bulk; a proof file over the policy limit or a base64 archive is refused by the gate and the push guard, and the files over the limit today are replaced by summaries without rewriting history
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: []
placement: [contracts, enforcement]
protected_paths: [".veldo/policy.yaml", "scripts/verify.sh", "scripts/veldo-guard.sh", "engine/scripts/veldo-guard.sh", "scripts/check_gate_mutations.py", "engine/scripts/check_gate_mutations.py", "scripts/suites/shared.py", "proof/VELDO-0123/manifest.json", "proof/VELDO-0215/manifest.json", "proof/VELDO-0230/manifest.json", "proof/VELDO-0189/older/digests.json"]
footprint:
  - ".veldo/policy.yaml"
  - ".veldo/validate.py"
  - "engine/.veldo/validate.py"
  - "scripts/veldo-guard.sh"
  - "engine/scripts/veldo-guard.sh"
  - "packs/*/hooks/pre-push"
  - "scripts/verify.sh"
  - "scripts/check_teeth_mutations.py"
  - "scripts/check_gate_mutations.py"
  - "engine/scripts/check_gate_mutations.py"
  - "scripts/parser_corpus_audit.py"
  - "scripts/writer_corpus_audit.py"
  - "scripts/suites/**"
  - "CLAUDE.md"
  - "VELDO.md"
  - "engine/VELDO.md"
  - "packs/*/**"
  - "proof/VELDO-0110/**"
  - "proof/VELDO-0121/**"
  - "proof/VELDO-0123/**"
  - "proof/VELDO-0189/**"
  - "proof/VELDO-0215/**"
  - "proof/VELDO-0230/**"
  - "proof/VELDO-0270/**"
  - "specs/VELDO-0270-proof-is-small-summaries-never-raw-bulk.md"
  - "specs/index.md"
behavior_bearing: true
observability:
  logs: >
    A refusal names the file, its size in bytes, the limit and where the limit was read from
    (.veldo/policy.yaml key proof.max_file_bytes, or the default of 1,048,576 bytes when the key is
    absent), or, for an encoded archive, the file, the byte offset of the encoded run and the archive
    kind its decoded bytes begin with. The push guard also names the ref and the commit that added the
    file.
  metrics: >
    None added. The contracts stage prints the count of proof files checked and the largest one with
    its size, so a bundle creeping toward the limit is visible before it is refused.
  error_taxonomy: >
    Two new refusals in the contract validator and the push guard: proof_file_over_limit and
    proof_encoded_archive. A third, proof_reference_dangling, for a manifest or summary that names a
    proof path absent from the tree. No existing refusal changes.
acceptance_criteria:
  - id: AC1
    text: >
      A PROOF FILE OVER THE LIMIT, OR A BASE64 ENCODED ARCHIVE AT ANY SIZE, IS REFUSED BY THE GATE AND
      BY THE PUSH GUARD. The limit is read from .veldo/policy.yaml, key proof.max_file_bytes, default
      1,048,576 bytes when the key is absent; a key that is present but not a positive integer is a
      refusal, never the default. (a) The gate's contract check (.veldo/validate.py all, run by the
      contracts stage of scripts/verify.sh, and its canon engine/.veldo/validate.py) refuses
      proof_file_over_limit for every file tracked under proof/ in the candidate tree larger than the
      limit, and proof_encoded_archive for every tracked proof file, of any size, that carries base64
      text decoding to an archive or compressed stream: a name ending .b64 or .base64, or a base64 run
      of 64 characters or more whose decoded bytes begin with the gzip, zip, bzip2, xz or zstd magic or
      carry the tar magic at offset 257. (b) The push guard (scripts/veldo-guard.sh and its canon
      engine/scripts/veldo-guard.sh, which the packs/*/hooks/pre-push hooks call) applies the same two
      rules, with the same limit read from the same key, to every commit a push to a protected ref would
      send that the remote does not already have, not only the tip, so a large file added in one commit
      and removed in the next is still refused. The protected refs are read from policy key
      proof.protected_refs, default refs/heads/main and refs/tags/*. Files already in history before
      the commit of AC3 are not re-judged; the check covers what a push adds. VELDO_EMERGENCY passes
      through as it does today and is recorded.
    falsified_by: >
      Registered rows with a green baseline, each on a scratch repository built by the suite: (1) a
      proof file of limit plus one byte reds the contract check with proof_file_over_limit naming the
      file and the limit's source, and a file of exactly the limit passes; (2) a 2 KB proof file holding
      a base64 gzip stream reds proof_encoded_archive, and a 2 KB file of base64 text that decodes to
      plain ASCII passes; (3) proof.max_file_bytes set to 2048 refuses a 3 KB file the default would
      pass, and set to "big" refuses the policy itself; (4) a push to main of two commits, the first
      adding a 2 MB proof file and the second deleting it, is refused by the guard naming the first
      commit; the same two commits pushed to an unprotected branch pass. A mutation that makes the
      guard read only the tip reds row (4); one that hard codes the default reds row (3).
  - id: AC2
    text: >
      PROOF KEEPS THE SUMMARY A REVIEWER NEEDS, AND THE PROOF TOOLING WRITES SUMMARIES, NOT RAW DUMPS.
      Every result a proof bundle records carries: the numbers that decide pass or fail (each with its
      bound and the verdict), the exact command that produced them, the environment (commit, tree,
      host, tool versions, and the load on the host when the result is timing sensitive), and, for any
      raw data the run produced and discarded, its file name, size in bytes and sha256. Raw data is
      not kept anywhere, in git or outside it. The tools that write into proof/ write that summary and
      never the raw dump: the gate transcript capture (the transcript scripts/verify.sh prints, copied
      into a bundle today as gate.log or full-gate.log.gz) becomes the stage table with each stage's
      verdict, seconds and the first failing row's detail; the mutation and falsifier writers
      (scripts/check_teeth_mutations.py, scripts/check_gate_mutations.py and its engine copy, and the
      proof drivers of the proof/*/drive.py form) write per case the case, the expected and observed
      verdict and the detail of each red, with a sha256 of the full result array instead of the array;
      the corpus audits (scripts/parser_corpus_audit.py, scripts/writer_corpus_audit.py) write counts
      and the differing entries, not the corpus. Veldo has no load harness of its own; a suite's load
      mode reports through the same summary form.
    falsified_by: >
      Registered rows: (1) each named writer, run on a fixture that produces more than the limit of raw
      output, writes a summary under the limit that holds the deciding numbers, the command, the
      environment and the sha256 of the discarded raw output, and the sha256 matches the raw bytes the
      fixture produced; (2) a mutation that makes a writer copy its raw output into the bundle reds
      row (1) through the AC1 contract check; (3) a summary missing the command or the sha256 of a
      discarded file is refused by the contract check as an incomplete summary.
  - id: AC3
    text: >
      THE FILES OVER THE LIMIT TODAY ARE DELETED FROM THE CURRENT TREE IN ONE COMMIT, EACH REPLACED BY
      A SHORT SUMMARY, AND HISTORY IS NOT REWRITTEN. The eight proof files over 1,048,576 bytes at main
      afa292f0 (proof/VELDO-0110/corpus-before.json 7,454,256 bytes, proof/VELDO-0121/results/AC4-red.json.gz,
      proof/VELDO-0121/earlier-attempt/results/AC4-red.json.gz, proof/VELDO-0230/gate.log,
      proof/VELDO-0189/older/971186ac.tar.gz, proof/VELDO-0189/older/8bc34e94.tar.gz,
      proof/VELDO-0123/removed-teeth.json, proof/VELDO-0215/full-gate.log.gz), and every base64 encoded
      archive AC1 finds, are removed in a single commit. Each is replaced by <name>.summary.json beside
      it, under the limit, carrying the original path, size in bytes, sha256 of the removed bytes, the
      commit in which they remain readable, and the deciding numbers the file held where they can be
      extracted (counts, verdicts, stage times, red rows), or the reason they cannot. Every manifest,
      README and digest record that named a removed file (proof/VELDO-0123/manifest.json,
      proof/VELDO-0215/manifest.json, proof/VELDO-0230/manifest.json, proof/VELDO-0189/older/digests.json
      and the others the contract check finds) names the summary instead, and the contract validator
      gains proof_reference_dangling so no proof path named anywhere in proof/ is absent from the tree.
      A manifest's recorded digest of a removed file stays as recorded; the summary's sha256 equals it.
      No commit is rewritten, no approval is re-recorded, and no ref is force pushed.
    falsified_by: >
      After the commit: the contract check over the whole tree is green with zero files over the limit
      and zero encoded archives; for each removed file, git show <commit before>:<path> | sha256sum
      equals the summary's sha256; a mutation that leaves one manifest naming a removed file reds
      proof_reference_dangling; git rev-list of main before the commit is a prefix of main after it,
      and every recorded approval still verifies against its commit.
  - id: AC4
    text: >
      THE RULE IS STATED WHERE BUILDERS AND REVIEWERS READ. CLAUDE.md, VELDO.md and its canon
      engine/VELDO.md (whose proof section adopters receive through packs/), state in one short
      paragraph: proof is small summaries, never raw bulk; the limit and where it is read from; base64
      archives are refused at any size; what a summary must carry (deciding numbers, command,
      environment, sha256 of discarded raw data); raw data is discarded, not stored elsewhere. The
      builder and reviewer briefs written for any Veldo spec carry the same paragraph verbatim, and the
      reviewer's checklist asks whether the bundle holds anything a reviewer does not need.
    falsified_by: >
      The docs check (scripts/check_docs.sh) fails when the paragraph is missing from or differs in any
      of the named files; a mutation that deletes it from engine/VELDO.md reds that check and the
      template sync check. Brief compliance is outside the gate: the owner's brief writers in the
      operator's workspace are checked by reading the next builder and reviewer brief issued after this
      spec lands.
required_evidence: [unit, integration]
rollback: >
  Revert the commits. The checks stop refusing large files and the writers return to raw output. The
  removed files are still readable at the commit before AC3's commit, so a revert of that commit
  restores them byte for byte; nothing has to be recovered from anywhere else.
---

## Intent

Proof exists so a reviewer can decide whether an acceptance criterion holds. A reviewer needs the
numbers that decide it, the command and the environment, and the digest of anything bulky that was
produced. Raw load records, full gate logs and pasted archives are not read by anyone, slow every
clone and worktree, and push the repository toward hosting limits. The owner's rule is that nothing in
proof should be larger than 1 MB and that bulky evidence is not kept at all.

## Context

The weight audit of 2026-11-06 (/home/dmitry/projects/myday/research/veldo-core-weight-audit-2026-11-07.md,
item 2) measured Veldo proof at 5,831 files and 108 MB, 1,636 of 3,372 commits touching proof/. At main
afa292f0 eight files are over 1,048,576 bytes; the largest is proof/VELDO-0110/corpus-before.json at
7.45 MB. The audit recommended moving large files to object storage; the owner rejected keeping them
anywhere. The same rule is specified for the core repository in its own spec.

## Out of scope

Rewriting history or shrinking .git; files outside proof/; the gate records tracked in .veldo (audit
item H); the size of specs, plans or code.

## What the reviewer judges

- The limit is read from policy in both checks, and an invalid key is a refusal, not the default.
- The push guard judges every commit a push sends to a protected ref, not only the tip.
- Each summary's sha256 matches the removed bytes, and its numbers match what the file held.
- No commit id changed and no manifest or digest record names a missing path.

## History

2026-11-07: drafted on the owner's decision, Telegram 39699 to 39704. The owner rejected keeping bulky
evidence anywhere ("Why would anything be larger than 1mb?", "Why do we need to keep it?") and agreed
to delete the existing big files from the current tree without rewriting history, since a rewrite
would change every commit id and break the approvals bound to them, to keep only summaries in proof,
and to refuse big files from now on. Evidence: the weight audit item 2. Nothing has been deleted yet.

2026-11-07: ready by the lead under the owner's narrowed approval scope (Telegram 39708: routine and test-machinery work no longer needs his sign-off; listed in his daily summary). The rule itself was his decision in 39704.
