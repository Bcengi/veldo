# VELDO-0217 review records

One file per reviewed batch, written by an independent reviewer under the repository's L2 rule, never
by the builder or the proposer. A declaration in scripts/mutation_case_inputs.json is qualified only
when its `review` field names a record here whose entry for that case binds the declaration's digest
and its proposal's trace digests (case_reuse.review_matches), and every mechanical condition of AC2
holds. The reviewed flag lands in scripts/mutation_case_inputs.json, a protected path, so each batch
also carries the owner's commit-bound approval. The records themselves are a protected path too
(`proof/VELDO-0217/reviews/*` in .veldo/policy.yaml), so writing or changing one needs the same
approval.

```json
{
  "schema": "veldo.case-input-review/v1",
  "batch": "<name>",
  "reviewer": "<who reviewed>",
  "commit": "<the commit the declarations were reviewed at>",
  "cases": {
    "<driver>:<case>": {
      "declaration": "<case_reuse.declaration_digest(declaration)>",
      "traces": ["<trace digest of each proposal run, in order>"]
    }
  }
}
```

No batch is reviewed yet: no record exists, so every declaration runs fresh (review_mismatch or
unreviewed_declaration), and until VELDO-0226 writes a sensitivity proof for a key, a reviewed one
would still run fresh (sensitivity_unproved).
