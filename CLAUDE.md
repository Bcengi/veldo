# Repository instructions

1. Read VELDO.md before changing anything.
2. The unit of work is a specification in specs/. Do not implement without a ready spec.
3. The canonical gate is ./scripts/verify.sh. Green is the only done.
4. Protected paths and merge policy: .veldo/policy.yaml.
5. Never approve your own implementation. Review runs in a fresh context.

## Proof is small summaries

Proof is small summaries, never raw bulk. No file under proof/ may be larger than the limit read from `.veldo/policy.yaml` key `proof.max_file_bytes` (1,048,576 bytes when the key is absent), and a base64 encoded archive is refused at any size; the gate's contract check and the push guard both refuse them. A summary carries the numbers that decide pass or fail with their bounds and verdicts, the exact command that produced them, the environment (commit, tree, host, tool versions, and host load when the result is timing sensitive) and, for every raw file the run produced, its name, size in bytes and sha256. Raw data is discarded, not stored elsewhere.

## This repository

This is the VELDO home repository: the method and its companion documents
(docs/), the Claude Code plugin that installs VELDO into other repositories
(packs/claude/), the product plans that govern VELDO's own development (plans/),
and the PDF rendering pipeline (scripts/render_pdfs.py + docs/manifest.yaml).
It runs VELDO on itself: every change to the method's machinery is a spec
with proof and independent review.

Always-true facts:
- engine/ is the canon. The repository's own .veldo/validate.py,
  .veldo/policy_check.py, scripts/update_index.py, and scripts/veldo-guard.sh
  are synced copies; the gate fails if they drift (template-sync check).
- Documents in docs/ (except docs/design/ provenance) are fully generic:
  zero company, product, or project references. The gate's docs check
  enforces this and the character rules (ASCII hyphens only, no non-ASCII).
- PDF rendering is a manual release act (needs Chrome CDP): run
  scripts/render_pdfs.py after doc changes and commit pdf/.
- Product plans live flat in plans/, contract veldo.plan/v1, validated by
  .veldo/validate.py; the specs index carries the plan status section.

## Specification identifiers: existing ones stay WARP, new ones are VELDO

Every specification, plan and proof bundle in this repository is keyed `WARP-nnnn`, because the method
was built under that internal name before it was published. **Those ids do not get renamed, and new
work is issued as `VELDO-nnnn` starting at VELDO-0001.**

This is a decision rather than an oversight, and the reason is the evidence. A proof bundle's identity
is bound to its content by digest, so renaming its id rewrites the bundle, which changes the digest,
which breaks the binding that made it evidence in the first place. Doing that across 147 bundles and
every cross-reference between them would produce records asserting that work happened under names it
never had. One visible seam, explainable in a sentence, is worth more than 12,700 edits that damage the
receipts they are tidying.

So: read a `WARP-nnnn` id as historical. Write `VELDO-nnnn`.
